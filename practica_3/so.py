#!/usr/bin/env python

from hardware import *
import log



## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)


## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            #print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)


    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)

## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):

         # obtengo el pcb del proceso que esta corriendo en cpu
        pcbKill = self.kernel.pcbTable.getRunningPCB()

        #salva el pc de cpu en el pcb de la variable pcbKill y pone el cpu en -1
        self.kernel.dispatcher.save(pcbKill)
        
        # pasar el estado a "terminated" con el pid del pcb dado 
        self.kernel.pcbTable.modificarStatePCB(pcbKill.getPid(), TERMINATED)
        
        # modificar el pc del pcb  
        #le pasamos el id pid del pcb que queremos modificar y el pc que queres que ponga
        self.kernel.pcbTable.modificarPcPCB(pcbKill.getPid(), pcbKill.getPc()) 

        #Limpiar la setRunningPcb, para que quede libre y podamos poner otro programa
        self.kernel.pcbTable.setRunningPcb(None)
            
         # verifico si la lista de la cola de ready no es vacia entonces:
        if(not self.kernel.readyqueue.isEmpty()):
            

            #creo una nueva variable con contenga un pcb nuevo
            # Obtiene el proximo pcb() de nextInQueue() en la READYQUEUE siguiendo la metodologia FIFO
            newPCB = self.kernel.readyqueue.nextInQueue()
            print(newPCB.getPc())
            # Modifica el estado del pcb() asignado a la variable newPCB a "running"
            self.kernel.pcbTable.modificarStatePCB( newPCB.getPid(),RUNNING)
            #Carga pcb() de la variable newPCB en el CPU()
            self.kernel.dispatcher.load(newPCB)
            #cargamos en pcb table el pcb que esta "running" ahora en cpu
            self.kernel.pcbTable.setRunningPcb(newPCB)

    ## Imprim iprime el aviso de programa finalizado
    log.logger.info(" Program Finished ")

      


class IoInInterruptionHandler(AbstractInterruptionHandler):

#la cpu lee una instruccion de I/O y genera una interrupcion, la recibe el interrup(??) vector y le avisa al so mediante el handler, al cual se le dan los atributos del pcb y queda a cargo el I/O
    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.pcbTable.getRunningPCB() #obtengo el pcb de lo que esta corriendo ahora
        self.kernel.dispatcher.save(pcb) #lo salvo
       
        #cambiar estado a waiting del pcb
        pcb.setState(WAITING)
        
        #modificar el estado del pcb en la pcb table con el pid de pcb
        self.kernel.pcbTable.modificarStatePCB(pcb.getPid(), WAITING)
         #el manejo del pcb queda ahora manenajo por el io
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        
        #consultar si la lista de ready queue no es vacia, si no es vacia, agarramos el proximo programa y le cambiamos el estado bla bla
        if (not self.kernel.readyqueue.isEmpty()):
            #newPcb = obtiene el proximo pcb de la ready queue 
            newPCB = self.kernel.readyqueue.nextInQueue()
            #cambia el estado del newPcb a running
            newPCB.setState(RUNNING)
             #modificamos el pc que ya estaba en la pcb tabla, por el nuevo pc
            #self.kernel._PCBTABLE.modificarPcPCB(newPCB.getPid(), newPCB.getPC())
            
            #lo carga en la tabla como el proceso que esta corriendo
            self.kernel.pcbTable.setRunningPcb(newPCB)
             #lo carga a dispatcher con load
            self.kernel.dispatcher.load(newPCB)
          
           
        ## Imprime el estado del ioDeviceController()    
        log.logger.info(self.kernel.ioDeviceController)
        

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        #obtiene un pcb del ioDevice cuando termina 
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        
        #si no hay nada corriendo en pcb table
        if(self.kernel.pcbTable.getRunningPCB() == None):
             #le cambia el estado al pcb y lo carga con dipatcher
             pcb.setState(RUNNING)
             self.kernel.dispatcher.load(pcb)
             #le cambia el estado en la pcb table
             self.kernel.pcbTable.modificarStatePCB(pcb.getPid(), RUNNING)
             # lo setea en running en la pcb table
             self.kernel.pcbTable.setRunningPcb(pcb)
        else:
            pcb.setState(READY)
            self.kernel.pcbTable.modificarStatePCB(pcb.getPid(), READY)
            self.kernel.readyqueue.add(pcb)
        #si no lo mismo pero en vez de running, ready
        
        
        #HARDWARE.cpu.pc = pcb['pc']
        log.logger.info(self.kernel.ioDeviceController)

class NewInterruptionHandler(AbstractInterruptionHandler):
       
    def execute(self, irq):
        program = irq.parameters
        #Se crea un pcb
        pid            = self.kernel.pcbTable.getNewPID()
        pc             = 0
        pcb            = PCB(pid, 0, pc, NEW)
        baseDir        = self.kernel.loader.load_program(program)
        pcb.setBaseDir(baseDir)
        pcb.setState(READY)
        
        #se agrega el pcb a la tabla de pcb table ya al finalizar todo
        self.kernel.pcbTable.add(pcb)
        
        #si no hay ningun proceso corriendo
        if(self.kernel.pcbTable.getRunningPCB() == None):
            pcb.setState(RUNNING) #se cambia el estado a running del pcb
            self.kernel.pcbTable.setRunningPcb(pcb) #y se setea el proceso actual en running en la pcb table
            self.kernel.dispatcher.load(pcb) #el dispach lo carga en cpu
        else:
            #se agrega a la lista de ready
            self.kernel.readyqueue.add(pcb)

        log.logger.info("HARDWARE after load: {hardware}".format(hardware=HARDWARE))
        
class Loader ():
    
    def __init__(self):
        self._baseDir = 0

    ## Carga el prograa dado en memoria
    def load_program(self, program):
        ## 
        progSize = len(program.instructions)
        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.write(self._baseDir, inst)
            self._baseDir += 1
        return self._baseDir - progSize 
    

class  Dispatcher():

    #Carga el pcb dado en la CPU
    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.getPc()               #PRACTICA 3: Se crea una variable en la cual se obtiene el PC del PCB
        HARDWARE.mmu.baseDir = pcb.getBaseDir()     #PRACTICA 3: Se crea una variabla en la cual se obtiene la baseDir del MMU   

    ## Salva el estado de PC en un PCB dado y pone el CPU en IDLE
    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu.pc)      #PRACTICA 3: Actualiza el PC del PCB
        HARDWARE.cpu.pc = -1                #PRACTICA 3: Se setea el PC del CPU en -1, poniéndolo en IDLE 


class PCB():
    
    #guarda el estado de cada proceso
    #Encapsula atributos y variables de un proceso
    def __init__ (self, pid, baseDir, pc, state):
        self._pid       = pid
        self._baseDir   = baseDir
        self._pc        = pc
        self._state     = state

    #Getter de PID
    def getPid(self):
        return(self._pid)
    
    #Getter de PC
    def getPc(self):
        return self._pc

    #Getter de baseDir 
    def getBaseDir(self):
        return self._baseDir

    #Setter de PC
    def setPc(self, pc): #cambiarPc
        self._pc = pc

    #Setter de state
    def setState(self, state): #cambiarState
        self._state = state

    #Setter de baseDir
    def setBaseDir(self, bDir): #modificarBaseDir
        self._baseDir = bDir
        
     # Setter de PID
    def setPid(self, pid):
        self._pid = pid    

    def __repr__(self):
        return "PID {pid}, State: {state}".format(pid=self._pid, state=self._state)
    


class PcbTable():

    def __init__(self):
        self._pidCounter = 0 
        self._table = {}  # Usamos un diccionario en lugar de una lista
        self._runningPcb = None

    def get(self, pid):
        return self._table.get(pid)  # Accedemos directamente al PCB por su PID

    def setRunningPcb(self, arg):
        self._runningPcb = arg

    def getRunningPCB(self):
        return self._runningPcb

    def add(self, pcb):
        new_pid = self.getNewPID()  # Obtenemos un nuevo PID
        pcb.setPid(new_pid)  # Asignamos el nuevo PID al PCB
        self._table[new_pid] = pcb  # Almacenamos el PCB en el diccionario con su nuevo PID como clave

    def remove(self, pid):
        if pid in self._table:
            del self._table[pid]  # Eliminamos el PCB usando su PID como clave

    def getNewPID(self):
        self._pidCounter += 1
        return self._pidCounter
    
    def modificarStatePCB(self, pid, state):
        pcb = self.get(pid)
        if pcb:
            pcb.setState(state)  # Modificamos el estado del PCB si se encuentra

    def modificarPcPCB(self, pid, pc):
        pcb = self.get(pid)
        if pcb:
            pcb.setPc(pc)  # Modificamos el contador de programa del PCB si se encuentra

    def repr(self):
        return [pcb.repr() for pcb in self._table.values()]  # Representamos todos los PCB en el diccionario

''' antiguo pcbtable
    class PcbTable():

    def __init__(self):
        self._pidCounter = 0 
        self._table = []
        self._runningPcb = None

    # Retorna el pcb con el pid proporcionado 
    def get(self, pid):
        for index in self._table:
            if pid == index.getPid():
                return index

    #
    def setRunningPcb(self, arg):
        self._runningPcb = arg

    # Retorna el pcb() que tiene el estado "running"
    def getRunningPCB(self):
        return self._runningPcb

    #Agrega un pcb a table
    def add(self, pcb):
        self._table.append(pcb)

    ## elimina el PCB con ese PID de la tabla 
    def remove(self, pid):
        varTem = []
        for index in self._table:
            if pid != index.getPid():
                varTem.extend([index])
        self._table = varTem

    ## Crea un _pid unico y lo retorna
    def getNewPID(self):                            
        self._pidCounter +=1
        return self._pidCounter
    
    
      ## Crea un _pid unico y lo retorna
   def getNewPID(self):
        if len(self._table) == 0:
            return 1
        else:
            return self._table[-1].getPid() + 1
    

    #Modifica el _state del pcb() que tiene el pid suministrado
    def modificarStatePCB(self, pid, state):
        for index in self._table:
            if pid == index.getPid():
                index.setState(state)
                break

    ## Modifica el _pc del pcb() que tiene el pid suministrado
    def modificarPcPCB(self, pid, pc):
        for index in self._table:
            if pid == index.getPid():
                index.setPc(pc)
                break

    def repr(self):
        listaPcb = []
        for elem in self._table:
            listaPcb.append(elem.repr())

        return listaPcb

'''
    

class READY_QUEUE():

#cola de programas en estado ready 
    def __init__(self):
        self._readyQueue = []

    def add(self, pcb):
        self._readyQueue.append(pcb)

    #te rotorna el pcb del proximo programa que sigue en la lista
    def nextInQueue(self):
        return(self._readyQueue.pop(0))
    
    def isEmpty(self):
        return(len(self._readyQueue) == 0)       
         

# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)

        #Práctica 3
        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        #Constantes - Instanciando objetos de las clases ready_queue y pcb_table, para no crear objetos a cada rato
        self._READYQUEUE = READY_QUEUE()
        self._PCBTABLE   = PcbTable()
        self._DISPATCHER = Dispatcher()
        self._LOADER = Loader()
        
    #Getters 
    
    @property
    def readyqueue(self):
        return self._READYQUEUE  
    
    @property
    def pcbTable(self):
        return self._PCBTABLE

    @property
    def dispatcher(self):
        return self._DISPATCHER

    @property
    def loader(self):
        return self._LOADER
    
    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    ## emulates a "system call" for programs execution
    def run(self, program):
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, program)
        HARDWARE.interruptVector.handle(newIRQ)

    def __repr__(self):
        return "Kernel "

NEW = "new"
RUNNING = "running"
READY = "ready"
WAITING = "waiting"
TERMINATED = "terminated"


        


