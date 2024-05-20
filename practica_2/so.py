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

   def execute(self, irq): #practica 2
        log.logger.info(" Program Finished ") #se le agrego log porque con logger solo no funcionaba
        self.kernel.loadNextProgram()



# emulates the core of an Operative System
class Kernel():

    def __init__(self):
        ## setup interruption handlers
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)
        self._programList = [] #creación de atributo el cual guarde en una lista los programas

    def load_program(self, program):
        # loads the program in main memory  
        progSize = len(program.instructions)
        for index in range(0, progSize):
            inst = program.instructions[index]
            HARDWARE.memory.write(index, inst)

  
        
         ## emulates a "system call" for programs execution
    def execute(self, program):
        self.load_program(program)
        log.logger.info("\n Executing program: {name}".format(name=program.name))
        log.logger.info(HARDWARE)

        # set CPU program counter at program's first intruction
        HARDWARE.cpu.pc = 0


    def executeBatch(self, batch): #practica 2
        self._programList = batch #guardo el batch (la lista de programas) en el atributo de la clase kernel
        self.execute(self._programList.pop())


    def __repr__(self):
        return "Kernel "

    def loadNextProgram(self): #practica 2
        HARDWARE.cpu.pc = -1
        if self._programList:
            self.execute(self._programList.pop())
        else:
            HARDWARE.switchOff()
