
# Grupo 01

## Integrantes:

| Nombre y Apellido    |      Mail                       |     usuario Gitlab    |
|----------------------|-------------------------------- |---------------------- |
| Nicole Soares        | nicolesoares918@gmail.com       |  Nicole-Soares        |
| Tobias Agustin Yegro | tobiyegro@gmail.com             |  tobiyegro            |
| Facundo Carnevale    | carnevalefacundo@gmail.com      |  carnevalefacundo     |




----------------------------------------------------------------

## Entregas:

### Práctica 1:  Aprobada

### Práctica 2:  Aprobada



### Práctica 3: Aprobada
 (solo queda esto para revisar, pero lo pueden aplicar en la P4)
 

- Deberian sacar estos 2 metodos del pcbTable: 

```
  modificarPcPCB()
  modificarStatePCB()
```
 


- Que impacto tiene esto ??
https://gitlab.com/24-s1-01/grupo-01/-/blob/main/practicas/practica_3/so.py?ref_type=heads#L111

`self.kernel.pcbTable.modificarPcPCB(pcbKill.getPid(), pcbKill.getPc()) `


- habria que cambiar los 

`self.kernel.pcbTable.modificarStatePCB(pcb.getPid(), XYZ)`

por 

`pcb.setState(XYZ)`

 


### Práctica 4:  Aprobada

#### Scheduler
- get next 
por que estan retornando una tupla ?
https://gitlab.com/24-s1-01/grupo-01/-/blob/main/practicas/practica_4/so.py?ref_type=heads#L521


- TimeoutInterruptionHandler
  Que pasa cuando se cumple el quantum y la ready queue esta vacia ??
  https://gitlab.com/24-s1-01/grupo-01/-/blob/main/practicas/practica_4/so.py?ref_type=heads#L110
  
    
  


#### Gantt

- Deberian usar las constantes en lugar de los Strings .
 
 https://gitlab.com/24-s1-01/grupo-01/-/blob/main/practicas/practica_4/so.py?ref_type=heads#L603
 
 https://gitlab.com/24-s1-01/grupo-01/-/blob/main/practicas/practica_4/so.py?ref_type=heads#L655

 
- por que lo activan en cada tick?
   https://gitlab.com/24-s1-01/grupo-01/-/blob/main/practicas/practica_4/so.py?ref_type=heads#L124






### Práctica 5: Aprobada (con mejoras para hablar en clase)

La práctica "esta bien", el unico "bug"/problema es: 

- MMU.baseDir: no se esta actualizando despues de compactar.
   Les esta faltando actualizar el MMU.baseDir con el baseDir  del runningPCB (hacerlo siempre o solo si detectan que cambio de lugar)

    

**...pero estan "calculando" todo siempre. Esto hace que el S.O. sea mas lento**

- Cada vez que quieras cargar un programa vas a tener que recorrer todos los PCBs y regenerar la lista debloques libres para ver si hay un bloque libre suficientemente grande
- Para calcular si va a entrar un programa (calcular la cantidadDeEspacioDisponible) tenes que recorrer todo tambien.


Deberian tener "cacheados" algunos datos para evitar ese re-calculo cada vez:


ejemplo: 

 
 - cantidadDeEspacioDisponible(): no seria necesario tener que hacer esta cuenta cada vez.
si tenemos una "variable" con la cantidadDeMoriaLibre (se inicializa con el tamaño de memoria y despues se suma/resta en cada free/alloc de memoria)



- getFreeBlocks()
 por que se crea esta lista cada vez que la necesito?
 deberian mantener la lista de bloques libres en una variable del MemoryManager y mantener esa lista (se modificaria en cada free/alloc)



### Práctica 6:  Aprobada


en el PCB: deberian renombrar la variable baseDir a pageTable 



