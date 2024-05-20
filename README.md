
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

 