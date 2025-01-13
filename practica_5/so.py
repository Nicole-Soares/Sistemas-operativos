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

    #tp 4
    def expropiate(self, pcbRunning, pcb):
        self.kernel.dispatcher.save(pcbRunning) #sacamos del cpu con dipatcher
        pcbRunning.setState("ready") #cambiamos estado
        self.kernel.scheduler.add(pcbRunning) #agregamos al scheduler
        self.kernel.pcbTable.setRunningPcb(pcb) #seteamos en pcb table el pcb nuevo en running
        pcb.setState("running")#cambio de estado
        self.kernel.dispatcher.load(pcb) #se carga
     

#tp 4
class TimeoutInterruptionHandler(AbstractInterruptionHandler):
    #interrupcion de cuando se le termina el tiempo al proceso
    def execute(self, irq):
        #si no es vacio la ready queue del scheduler entonces (si no esta vacia es porque algo esta corriendo)
        if not (self.kernel.scheduler.isEmpty()):
            #guardo en una variable lo que esta corriendo
            pcbRunning = self.kernel.pcbTable.getRunningPCB()
            #traigo el que sigue de la lista
            newPcb = self.kernel.scheduler.nextInQueue()
            #lo expropio, osea saco el que corria por el que sigue
            self.expropiate(pcbRunning, newPcb['pcb'])
        
        HARDWARE.timer.quantum(self, 3)    #actualizo el quantum

        log.logger.info(self.kernel.pcbTable.__repr__())

class StatInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        self.kernel.scheduler.checkTick()
        #self.kernel.diagramaDeGantt.activateGantt()
        self.kernel.diagramaDeGantt.doGantt()

class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):

         # obtengo el pcb del proceso que esta corriendo en cpu
        pcbKill = self.kernel.pcbTable.getRunningPCB()

        #salva el pc de cpu en el pcb de la variable pcbKill y pone el cpu en -1
        self.kernel.dispatcher.save(pcbKill)
        
        # pasar el estado a "terminated" con el pid del pcb dado 
        pcbKill.setState(TERMINATED)
        
        # modificar el pc del pcb  
        #le pasamos el id pid del pcb que queremos modificar y el pc que queres que ponga
        #self.kernel.pcbTable.modificarPcPCB(pcbKill.getPid(), pcbKill.getPc()) 

        #Limpiar la setRunningPcb, para que quede libre y podamos poner otro programa
        self.kernel.pcbTable.setRunningPcb(None)
        
        # Saco el PCB de la pcbTable
        self.kernel.pcbTable.remove(pcbKill.getPid())
        # Libero el espacio en la memoria
        self.kernel.memoryManager.liberarBloque(pcbKill.getBaseDir(), pcbKill.getProgramSize())

        #Si la waiting queue es vacia:
        #if(self.kernel.waitingQueue.isEmpty()):
        # verifico si la lista de la cola de ready no es vacia entonces:
        if(not self.kernel.scheduler.isEmpty()):
            #creo una nueva variable con contenga un pcb nuevo
            # Obtiene el proximo pcb() de nextInQueue() en la READYQUEUE siguiendo la metodologia FIFO
            nextInQueue = self.kernel.scheduler.nextInQueue() #recibe un pcb, no un diccionario
            #cambia el estado del newPcb a running
            #newPCB = nextInQueue['pcb']
            nextInQueue.setState(RUNNING)
            #Carga pcb() de la variable newPCB en el CPU()
            self.kernel.dispatcher.load(nextInQueue)
            #cargamos en pcb table el pcb que esta "running" ahora en cpu
            self.kernel.pcbTable.setRunningPcb(nextInQueue)
            #Si la waiting queue no es vacia:
           # else:
            #    newIRQ = IRQ(NEW_INTERRUPTION_TYPE, self.kernel.waitingQueue.nextInQueue())
             #   HARDWARE.interruptVector.handle(newIRQ)



    ## Imprime el aviso de programa finalizado
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
        #self.kernel.pcbTable.modificarStatePCB(pcb.getPid(), WAITING)
         #el manejo del pcb queda ahora manenajo por el io
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        
        #consultar si la lista de ready queue no es vacia, si no es vacia, agarramos el proximo programa y le cambiamos el estado bla bla
        if (not self.kernel.scheduler.isEmpty()):
            #newPcb = obtiene el proximo pcb de la ready queue 
            nextInQueue = self.kernel.scheduler.nextInQueue()
            #cambia el estado del newPcb a running
            #newPCB = nextInQueue['pcb']
            nextInQueue.setState(RUNNING)
             #modificamos el pc que ya estaba en la pcb tabla, por el nuevo pc
            #self.kernel._PCBTABLE.modificarPcPCB(newPCB.getPid(), newPCB.getPC())
            
            #lo carga en la tabla como el proceso que esta corriendo
            self.kernel.pcbTable.setRunningPcb(nextInQueue)
             #lo carga a dispatcher con load
            self.kernel.dispatcher.load(nextInQueue)
          
           
        ## Imprime el estado del ioDeviceController()    
        log.logger.info(self.kernel.ioDeviceController)
        

class IoOutInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        #obtiene un pcb del ioDevice cuando termina 
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        pcbRunning = self.kernel.pcbTable.getRunningPCB()
        #si no hay nada corriendo en pcb table
        if(pcbRunning == None):
             #le cambia el estado al pcb y lo carga con dipatcher
             pcb.setState(RUNNING)
             self.kernel.dispatcher.load(pcb)
             #le cambia el estado en la pcb table
             #self.kernel.pcbTable.modificarStatePCB(pcb.getPid(), RUNNING)
             # lo setea en running en la pcb table
             self.kernel.pcbTable.setRunningPcb(pcb)
        #cada vez que haya que agregar a la ready queue hay que preguntar si hay que expropiar (diapos)    
        elif (self.kernel.scheduler.mustExpropiate(pcbRunning, pcb)):
            self.expropiate(pcbRunning, pcb)
        else:
            pcb.setState(READY)
            #self.kernel.pcbTable.modificarStatePCB(pcb.getPid(), READY)
            self.kernel.scheduler.add(pcb)
        #si no lo mismo pero en vez de running, ready
        
        
        #HARDWARE.cpu.pc = pcb['pc']
        log.logger.info(self.kernel.ioDeviceController)
"""
class WaitingQueue():
    def __init__(self):
        self._waitingQueue = []
        self._waitingQueueCopia = waitingQueue
    
    def add(self, program):
        self._waitingQueue.append(program)
    
    def nextInQueue(self):
        return self._waitingQueue.pop(0)
    
    def isEmpty(self):
        return(len(self._waitingQueue) == 0)  
    
    #getters
    @property
    def waitingQueueCopia(self):
        return(self._waitingQueueCopia)
    
     #Setter 
    def setWaitingQueue(self, lista): 
        self._waitingQueue = lista
"""
class NewInterruptionHandler(AbstractInterruptionHandler):
       
    def execute(self, irq):
        parameters = irq.parameters
        program = parameters['program']
        priority = parameters['priority']

        #Se crea un pcb
        pid            = self.kernel.pcbTable.getNewPID()
        pc             = 0
        pcb            = PCB(pid, 0, pc, NEW, priority, len(program.instructions))
        baseDir        = self.kernel.loader.load_program(program, self.kernel.memoryManager)
        log.logger.info("--- BASE DIR: {baseDir} PROGRAM SIZE: {programSize}".format(baseDir=baseDir, programSize=pcb.getProgramSize()))
        
     #BaseDir puede ser None si no existe espacio en la memoria
        if baseDir is None:
            # Si no existe espacio en la memoria...
            # TODO: implementar WaitingQueue 
            #self.kernel.waitingQueue.add(parameters)  
            raise Exception("No hay lugar en memoria")
        else:
            # Si existe espacio en la memoria ...
            pcb.setBaseDir(baseDir)
            pcb.setState(READY)
            
            #se agrega el pcb a la tabla de pcb table ya al finalizar todo
            self.kernel.pcbTable.add(pcb)
            
            pcbRunning = self.kernel.pcbTable.getRunningPCB()
            #si no hay ningun proceso corriendo
            if(pcbRunning == None):
                pcb.setState(RUNNING) #se cambia el estado a running del pcb
                self.kernel.pcbTable.setRunningPcb(pcb) #y se setea el proceso actual en running en la pcb table
                self.kernel.dispatcher.load(pcb) #el dispach lo carga en cpu
            #cada vez que haya que agregar a la ready queue hay que preguntar si hay que expropiar (diapos)
            elif (self.kernel.scheduler.mustExpropiate(pcbRunning, pcb)):
                self.expropiate(pcbRunning, pcb)
            else:
                #se agrega a la lista de ready
                self.kernel.scheduler.add(pcb)

        log.logger.info("HARDWARE after load: {hardware}".format(hardware=HARDWARE))
    
    """def tryAssignWaitingPrograms(self):
        # Intentar asignar programas de la cola de espera mientras haya espacio en la memoria
        baseDir = None #seteo en none
        while not self.kernel.waitingQueue.isEmpty() and baseDir == None: #mientras no esta vacia la cola de waitingQueue y la baseDir no sea none
            nextProgram = self.kernel.waitingQueue.nextInQueue() #traigo el otro programa que sigue (me modifica la lista tambien)
            baseDir = self.kernel.loader.load_program(nextProgram, self.kernel.memoryManager) #me traigo su base dir
          
           
        if baseDir is not None: #si salgo del while puede ser porque baseDir no sea none
                nextProgram.setBaseDir(baseDir)
                nextProgram.setState(READY)
                self.kernel.pcbTable.add(nextProgram)
                # Si no hay ningún proceso en ejecución, cargar el programa en el CPU
                if self.kernel.pcbTable.getRunningPCB() is None:
                    nextProgram.setState(RUNNING)
                    self.kernel.pcbTable.setRunningPcb(nextProgram)
                    self.kernel.dispatcher.load(nextProgram)
                    
        #si salio porque se vacio, no hace nada
        self.kernel.waitingQueue.setWaitingQueue(self.kernel.waitingQueue.waitingQueueCopia)
    """     
            
            
class Loader ():
    
    def __init__(self):
        self._baseDir = 0

    ## Carga el prograa dado en memoria
    def load_program(self, program, memory_manager):
        ## 
        progSize = len(program.instructions)
        baseDir = memory_manager.getFreeBlock(progSize)
        
        # Si existe una posicion para poner el programa actual
        if baseDir is not None:
            self._baseDir = baseDir
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
        HARDWARE.timer.reset()
         
    ## Salva el estado de PC en un PCB dado y pone el CPU en IDLE
    def save(self, pcb):
        pcb.setPc(HARDWARE.cpu.pc)      #PRACTICA 3: Actualiza el PC del PCB
        HARDWARE.cpu.pc = -1                #PRACTICA 3: Se setea el PC del CPU en -1, poniéndolo en IDLE 


class PCB():
    
    #guarda el estado de cada proceso
    #Encapsula atributos y variables de un proceso
    def __init__ (self, pid, baseDir, pc, state, prioridad, programSize):
        self._pid       = pid
        self._baseDir   = baseDir
        self._pc        = pc
        self._state     = state
        self._prioridad = prioridad # ahora los programas tienen prioridad
        self._programSize = programSize
     
      #tp 4 guardamos los ticks de cada programa en su pcb
    def getTick(self):
        return self._tickIng
    
    def setTick(self, nuevoTick):
        self._tickIng = nuevoTick

    #Getter de PID
    def getPid(self):
        return(self._pid)
    
    #Getter de PC
    def getPc(self):
        return self._pc
    
    #Getter de priority
    def getPriority(self):
        return self._prioridad

    #Getter de baseDir 
    def getBaseDir(self):
        return self._baseDir

    #Getter de state
    def getState(self):
        return(self._state)

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
        
    def getProgramSize(self):
        return self._programSize  

    def __repr__(self):
        return "PID {pid}, State: {state}".format(pid=self._pid, state=self._state)
    


class PcbTable():

    def __init__(self):
        self._pidCounter = 0 
        self._table = {}  # Usamos un diccionario en lugar de una lista
        self._runningPcb = None

    def getTable(self):
        return(self._table)

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
    
    """
    def modificarStatePCB(self, pid, state):
        pcb = self.get(pid)
        if pcb:
            pcb.setState(state)  # Modificamos el estado del PCB si se encuentra

    def modificarPcPCB(self, pid, pc):
        pcb = self.get(pid)
        if pcb:
            pcb.setPc(pc)  # Modificamos el contador de programa del PCB si se encuentra
    """
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
'''  ya no existe ready queue como componente individual, ahora el scheduler se hace cargo
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
 ''' 

#Práctica 4      
#scheduler padre -- se encarga de la ready queue  
class Scheduler():
    #en el padre no hay que poner nada porque sus hijos se van a encargar el modo?

    def __init__(self):
        pass

    def add(self, pcb):
        pass

    def nextInQueue(self):
        pass

    def isEmpty(self):
        pass

    def mustExpropiate(self, pcbRunning, pcb ):
        return False

    def checkTick(self):
        pass


class SchedulerFiFo(Scheduler):
    
    def __init__(self):
        self._readyQueue = []
    
    def add(self, pcb):
        self._readyQueue.append(pcb)
    
    def nextInQueue(self):
        return self._readyQueue.pop(0)
    
    def isEmpty(self):
        return(len(self._readyQueue) == 0)  
    
    
class SchedulerPriorityNoExp(Scheduler): 
    def __init__(self):
        self._readyQueue = [[], [], [], [], []] #la cantidad de listas es equivalente a las prioridades, adentro hay diccionarios/ max prioridad 5/ indice de 0 a 4
        self._ticksParaEnvejecer = 4 #cada 4 ticks envejece el programa
        
    def add(self, pcb):
        priority = pcb.getPriority()
        psItem = {'tick': HARDWARE.clock.currentTick, 'pcb': pcb, 'priority': priority} #se crea un diccionario, el harware.clock guarda el tiempo actual
                   #clave-valor
        self._readyQueue[priority - 1].append(psItem) #se agrega a la ready que en su prioridad correspondiente, se le resta 1 porque el indice empieza en 0
    
    def checkTick(self):
        if self._ticksParaEnvejecer == 0: #chequeamos si ya se hicieron los ticks correspondientes
            self.tiempoParaEnvejecer() #se envejece
            self._ticksParaEnvejecer = 4 #se reinicia
        else:
            self._ticksParaEnvejecer -= 1 #se descuenta de uno en uno
    
    def tiempoParaEnvejecer(self):
        indice = 1
        while (indice < 5): #mientras indice sea < 5, los indices empiezan desde 0
            self.envejecer(self._readyQueue[indice], self._readyQueue[indice - 1]) #envejecemos los programa que esten la lista del indice (indice) dado y le pasamos la lista anterior (prioridad que le sigue) por si tiene que cambiarlo de prioridad
            indice += 1
    
    def envejecer(self, arr, poner): # la lista de procesos actuales y el los que le siguen por prioridad
        while bool(arr) and (4 + arr[0]['tick'] <= HARDWARE.clock.currentTick): #mientras no sea vacía y el tick con el que entro el primer elemento (un programa) de la lista + 4 (tiempo de ticks para envejecer)
            #me fijo a cuantos ticks el programa deberia envejecer, sumandole desde que entro mas lo que tiene que esperar, si los ticks actuales son mayores a los que tenia que esperar el programa, se envejece porque ya paso el tiempo de espera
            arr[0]['priority'] -= 1 #al primer programa del array, le aumento su prioridad
            poner.append(arr.pop(0))  #se pone y se borra con pop
    
    def nextInQueue(self):
        for index in self._readyQueue:
            if bool(index): #mientras no este vacia
                psItem = index.pop(0) # traigo y elimino de la cola el primer elemento
                return psItem['pcb']
    
    def isEmpty(self):
        return not (self._readyQueue[0] or self._readyQueue[1] or self._readyQueue[2] or self._readyQueue[3] or self._readyQueue[4]) 
                
class SchedulerPriorityExp(SchedulerPriorityNoExp):
    
    def mustExpropiate(self, pcbRunning, pcb):
        return pcb.getPriority() > pcbRunning.getPriority()       #Retorna si la prioridad del PCB en CPU es menor a la prioridad del PCB en RQ, para hacer la expropiacion 


class SchedulerRoundRobin(SchedulerFiFo): 
    def __init__(self):
        super().__init__()
        self.setearTimer(3)         #Seteo el quantum en 3 y activo el timer.
    
    def setearTimer(self, quantum):     
        HARDWARE.timer.quantum(self, quantum)   #se activa el timer para que empiece a contar los ticks y si son mayores o iguales al quantum, manda una interrupcion de time out  para expropiar   

# El LOADER se comunica con el MemoryManager cuando necesita alojar un programa en memoria
# Chequea en memoria si existe un tamaño disponible para alojar el programa
# Si existe, le paso al LOADER un BaseDir
# Si no existe, se intenta compactar la memoria para tener un espacio disponible.
class MemoryManager():
    
    def __init__(self, kernel):
        self._kernel = kernel
        
        ##devuelve una lista de bloques libres, recorre de forma ordenada los pcb
    
    def getFreeBlocks(self):
        # pcbTable = self._kernel.getPcbTable().getTable()
        free_blocks = []#lista de tuplas
        # Valor inicial antes de cargar el primer pcb
        progrEnd = -1 #0
        # Recorro la lista de bloques llenos
        for pcb in self.getOrderedPCBList(): #recorro pcb
            baseDir = pcb.getBaseDir()  #traigo baseDir 0 6
            progSize = pcb.getProgramSize()  #el tamaño del programa 1
            # Chequeo si hay un espacio vacio entre el programa actual y el anterior
            if baseDir > (progrEnd + 1): #si la base dir es mayor a donde finaliza el programa anterior (+ 1 porque el base dir de un programa siguiente siempre va a ser mayor a donde finaliza otro, por ende    
                                         # si es aun mas grande que el proximo baseDir(el que le corresponde por ser siguiente)es porque hay un hueco )
                # Hay un espacio vacio entre este programa y el anterior
                free_blocks.append((progrEnd + 1, baseDir - progrEnd - 1)) #donde empieza el bloque vacio (osea donde finaliza el programa + 1) y su tamaño (donde baseDir del anterior programa menos donde finaliza menos 1 porque se empieza desde 0) 
            # Actualizo la posicion del fin del programa actual
            progrEnd = baseDir + progSize - 1 #donde finaliza el programa anterior - 1 porque el programa puede finalizar donde empezo
        memoryEnd = HARDWARE.memory.size - 1 #le restamos 1 porque se maneja con indices, si pido el tamaño de la memoria me da 20 pero en realidad es de 0 a 19, su ultima posicion es 19
        # Chequeo si hay lugar al final de la memoria
        if memoryEnd > progrEnd: #si la ultima posicion de la memoria es mayor a donde termino el ultimo programa
            free_blocks.append((progrEnd + 1, memoryEnd - progrEnd)) #le agrego los bloques vacios
        return free_blocks
        
    # Retorna una lista de pares, donde el primer elemento del par es el inicio del programa y el segundo elemento es el tamaño
    def getOrderedPCBList(self):
        pcbList = []
        # Recorro los pcb para generar la lista de tuplas
        for _, pcb in self._kernel.pcbTable.getTable().items():
            pcbList.append(pcb)
        # Retorno la lista de PCB ordenada por baseDir
        return sorted(pcbList, key=lambda pcb: pcb.getBaseDir())

#chequea si hay un bloque libre del tamaño pedido
    def getFreeBlock(self, programSize):
        log.logger.info('-------------- Pidiendo un bloque a la memoria de tamaño {programSize} --------------'.format(programSize=programSize))
        log.logger.info(HARDWARE.memory)
        baseDirDelBloqueLibre = self.bloqueLibreDeTamanio(programSize)
        if baseDirDelBloqueLibre is not None:
            return baseDirDelBloqueLibre
        # Chequeo si existe espacio disponible total en la memoria sin compactar
        elif self.hayEspacioDisponible(programSize):
            # compacto y devuelvo el base dir despues de compactar
            self.compactarMemoria()
            # Retorno el base dir del primer bloque disponible
            return self.bloqueLibreDeTamanio(programSize)
        else:
            # No hay espacio ni compactando
            return None
            
    def bloqueLibreDeTamanio(self, programSize):
        # Obtengo la lista de bloques vacios
        free_blocks = self.getFreeBlocks()
        for baseDir, size in free_blocks:
            # Si el tamaño del bloque actual es mayor al tamaño del programa, retorno el baseDir del bloque actual
            if size >= programSize:
                return baseDir
            
    def liberarBloque(self, baseDir, size):
        # Recorro cada una de las direcciones partiendo de baseDir hasta el final del bloque
        for actualDir in range(baseDir, baseDir + size):
            # Libero el espacio en la memoria
            HARDWARE.memory.write(actualDir, '')
            
    def cantidadDeEspacioDisponible(self):
        # Devuelvo la cantidad de espacio disponible que existe en memoria
        cantidadDeCeldasLibres = 0
        bloquesVacios = self.getFreeBlocks()
        for _, cantidad in bloquesVacios:
            cantidadDeCeldasLibres += cantidad
        return cantidadDeCeldasLibres
            
    def hayEspacioDisponible(self, tamanio):
        return self.cantidadDeEspacioDisponible() >= tamanio   
    
    def compactarMemoria(self):
        log.logger.info('-------------- Compactando memoria --------------')
        log.logger.info(HARDWARE.memory)
        ### Freno el reloj del CPU
        HARDWARE.clock.stop()
        # Inicializo mi cabezal en 0
        cabezal = 0
        # Recorro la lista ordenada de PCB
        for pcb in self.getOrderedPCBList():
            baseDirActual = pcb.getBaseDir()
            # Si la posicion del bloque actual es mayor a la posicion del cabezal
            # Significa que hay espacio libre entre el cabezal y el proximo bloque
            if baseDirActual > cabezal:
                # Actualizo la posicion del PCB a la posicion del cabezal (muevo el bloque)
                self.subirBloqueNPosiciones(pcb, baseDirActual - cabezal)
                log.logger.info('Subiendo el pcb {pcb} con programSize {pSize} {posiciones} posiciones'.format(pSize=pcb.getProgramSize(), pcb=pcb.getBaseDir(), posiciones=baseDirActual - cabezal))
                #Actualizo el PCB
                pcb.setBaseDir(cabezal)
                cabezal = cabezal + pcb.getProgramSize()
            else:
                # Paso al siguiente bloque
                cabezal += pcb.getProgramSize()
        # TODO: actualizar la direccion de la ejecucion actual ?? ya se cambio
        # ...
        # Vuelvo a arrancar el clock
        HARDWARE.clock.start()
        log.logger.info('-------------- Finalizando la compactacion de memoria --------------')
        log.logger.info(HARDWARE.memory)
            
    def subirBloqueNPosiciones(self, pcb, cantidadPosiciones):
        # Dado un PCB y una cantidad de posiciones, tengo que mover el programa cantidadPosiciones posiciones hacia arriba
        dirActual = pcb.getBaseDir()
        programSize = pcb.getProgramSize()
        # Repeticion simple de programSize veces
        for _ in range(0, programSize):
            #contenidoAMover = HARDWARE.memory.read(dirActual)
            #HARDWARE.memory.write(dirActual - cantidadPosiciones, contenidoAMover)
            contenidoAMover = HARDWARE.memory.read(dirActual)
            # Muevo el contenido cantidadPosiciones posiciones
            HARDWARE.memory.write(dirActual - cantidadPosiciones, contenidoAMover)
            # Vacio la posicion actual
            HARDWARE.memory.write(dirActual, '')
            # Paso a la siguiente direccion
            dirActual += 1 

class DiagramaDeGantt():    
    def __init__(self, pcbtable):
        self._pcbTable = pcbtable       
        self._pcbTableCopy = []
        self._headers = []
        self._isActivated = False

#getters
    @property
    def isActivated(self):
        return(self._isActivated)
    
    @property
    def pcbTableCopy(self):
        return(self._pcbTableCopy)
    
    @property
    def headers(self):
        return(self._headers)
    

    def allPCBTerminated(self):             #Indica si todos los pcb en la pcb table tienen el estado "Terminated"
        for pid, pcb in self._pcbTable.getTable().items(): #llega un diccionario de la pcb table, separo por clave-valor
            if pcb.getState() != "terminated":       #Por cada PCB de la pcb table, si alguno tiene un estado diferente a "terminated", retorna falso. De caso contrario, retorna verdadero.
                return False
        return True
    
    def tickInformation(self):
        arrayPorTick = []
        for pid, pcb in self._pcbTable.getTable().items():       
            arrayPorTick.append(pcb.getState())          #Guarda los estados de todos los pcb de la pcb table por cada tick en un array. ["runnning", "waiting", "ready"]
        self._pcbTableCopy.append(arrayPorTick)          #cuando ya recorrio todos los estados de todos los programas, lo agrega como una lista a pcTableCopy [["runnning", "waiting", "ready"], []]
                                                        #                tick 1                          tick 2
                                                        # ejemplo : [["ready", "waiting", "running"], ["blabla", "blabla", "blabla"]] se guarda los estados de cada programa en cada tick

    #Hace un print del diagrama de Gantt, con formato de tabla "grid" y estableciendo como headers (columnas) los indices de cada programa.
    def printGantt(self):
        print(tabulate(self.mapGantt(), tablefmt = "grid", showindex = True, headers= self.headersGantt()))                                                                                                                  

    def activateGantt(self):
        self._isActivated = True

    def desactivateGantt(self):
        self._isActivated = False         

    
    def transposedArray(self):    
        # Junto el historial de estados de cada programa  
        programs = zip(*self.pcbTableCopy) #genera "filas", junta en tuplas todos los estados del primer programa, del segundo, etc ej: [["Running", "waiting", "terminated"], ["blabla", "blabla", "blabla"]]
                                                                                                                                         # programa1 = ("Running", "blabla"), programa 2 =("waiting", "blabla"), programa 3 =("terminated", "blabla")  varia segun los ticks        
                                            #zip agarra dos o mas listas y forma tuplas con los primero elementos, segundos, etc si sobra alguno lo descarta, en este caso no sobran porque dice terminated si terminaron, osea siempre hay un estado

        # Transformo en listas
        return list(map(list, programs)) #hace un map, el cual por cada elemento lo transforma en una lista y despues en una lista de listas

    def headersGantt(self):
        for index, sublist in enumerate(self.pcbTableCopy):       #Establece los headers (columnas) del gantt, enumerando según la longitud de la pcb table.
            self._headers.append(index) #las columnas van a ser los indices
        return self._headers    

    def mapGantt(self):
        # Transformo las listas de ticks en listas por programa
        transposedArray = self.transposedArray() #ya es una lista de listas ordenada por programa y de sus estados segun todos los ticks que hubo
        # mapea cada elemento (con el sublist) de la lista de listas (transposedArray) y usa una funcion anonima la cual "cambia" el estado por letras
        parsedArray = []
        for lista in transposedArray:
            parsedArray.append(self.cambiarPorLetras(lista)) 
        return parsedArray
    
    def cambiarPorLetras(self, lista):
        nuevaLista = []
        for estado in lista:
            if estado == TERMINATED:
                nuevaLista.append("T")
            elif estado == READY:
                nuevaLista.append(".")  
            elif estado == WAITING:
                nuevaLista.append("W") 
            else: nuevaLista.append("R")
        return nuevaLista
    """ 
            match estado:
                case TERMINATED:
                    nuevaLista.append("T")
                case "ready":
                    nuevaLista.append(".")
                case "waiting":
                    nuevaLista.append("W")
                case _:
                    nuevaLista.append("R")
        return nuevaLista
    """   
    def doGantt(self): #hacer el diagrama
        self.tickInformation()
        if(self.isActivated and self.allPCBTerminated()): #si esta activado y todos los pcb terminaron
            self.printGantt() #se hace el diagrama
            self.desactivateGantt() #se desactiva

class Crontab():

    def __init__(self, kernel):
            self._jobs = {} #diccionario
            self._kernel = kernel
            # nos subscribimos al Clock para recibir cada click
            HARDWARE.clock.addSubscriber(self)

    def add_job(self, tickNbr, program, prioridad):

        job = {'program': program, 'prioridad': prioridad}
        # en cada tick se pueden mandar a correr solo un job
        # se decidio asi para evitar complejidad en el emulador
        self._jobs[tickNbr] = job
        log.logger.info("Crontab: add job {job} to Tick {tickNbr} ".format(job = job, tickNbr = tickNbr))


    def tick(self, tickNbr):
        job = self._jobs.get(tickNbr)
        # Si hay algo para correr en este tick
        # lo mandamos a ejecutar
        if job != None:
            log.logger.info("Tick {tickNbr} - Running job: {job}".format(job = job, tickNbr = tickNbr))
            self.run_job(job)


    def run_job(self, job):
        program = job['program']
        prioridad = job['prioridad']
        self._kernel.run(program, prioridad)


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

        #Práctica 4
         #Tp 4
         #se crea un objeto de ese tipo y se registra en el interruptVector
        timeoutHandler = TimeoutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)

        #statHandler = StatInterruptionHandler(self) 
        #HARDWARE.interruptVector.register(STAT_INTERRUPTION_TYPE, statHandler)

        #tp 4
        #HARDWARE.cpu.enable_stats = True #para que se active el stats del cpu que esta en hardware

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice)

        #Constantes - Instanciando objetos de las clases ready_queue y pcb_table, para no crear objetos a cada rato
        #self._READYQUEUE = READY_QUEUE()
        self._PCBTABLE   = PcbTable()
        self._DISPATCHER = Dispatcher()
        self._LOADER = Loader()
        #tp 4
        self._DIAGRAMA_DE_GANTT = DiagramaDeGantt(self.pcbTable)
        self._MEMORY_MANAGER = MemoryManager(self)
        #Tp 4
        #self._SCHEDULER = SchedulerFiFo()
        #self._SCHEDULER = SchedulerPriorityNoExp()
        #self._SCHEDULER = SchedulerRoundRobin()
        self._SCHEDULER = SchedulerPriorityExp()
        self._crontab = Crontab(self)
        #TP 5
        #self._WAITINGQUEUE = WaitingQueue()

    @property
    def crontab(self):
        return self._crontab


        
    
    #Getters 
    
   # @property
    #def readyqueue(self):
     #   return self._READYQUEUE  
    
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
    
    #Tp 4
    @property
    def scheduler(self):
        return self._SCHEDULER
    
    @property
    def diagramaDeGantt(self):
        return self._DIAGRAMA_DE_GANTT
    
    @property
    def memoryManager(self):
        return self._MEMORY_MANAGER

   # @property
    #def waitingQueue(self):
     #   return self._WAITINGQUEUE

    ## emulates a "system call" for programs execution
    def run(self, program, priority): #ahora le llega la prioridad para los scheduler de eso
        self.diagramaDeGantt.activateGantt()
        parameters = {'program': program, 'priority': priority}
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, parameters)
        HARDWARE.interruptVector.handle(newIRQ)
        

    def __repr__(self):
        return "Kernel "
    

NEW = "new"
RUNNING = "running"
READY = "ready"
WAITING = "waiting"
TERMINATED = "terminated"
      


