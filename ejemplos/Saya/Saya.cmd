; Comandos
[Remap]
x = x
y = y
z = z
a = a
b = b
c = c
s = s

[Defaults]
command.time = 15
command.buffer.time = 1

;-| Botones |----------------------------------------------------------------
[Command]
name = "a"
command = a
time = 1

[Command]
name = "b"
command = b
time = 1

[Command]
name = "c"
command = c
time = 1

[Command]
name = "x"
command = x
time = 1

[Command]
name = "y"
command = y
time = 1

[Command]
name = "z"
command = z
time = 1

[Command]
name = "s"
command = s
time = 1

;-| Mantener presionado (los usa el juego para caminar, agacharse y cubrirse) |-
[Command]
name = "holdfwd"
command = /$F
time = 1

[Command]
name = "holdback"
command = /$B
time = 1

[Command]
name = "holdup"
command = /$U
time = 1

[Command]
name = "holddown"
command = /$D
time = 1

[Command]
name = "recovery"
command = x+y
time = 1

;-| Correr |-----------------------------------------------------------------
[Command]
name = "FF"
command = F, F
time = 10

[Command]
name = "BB"
command = B, B
time = 10

;---------------------------------------------------------------------------
; >>> SIMPLE-MODE commands >>>
; Esto lo escribe el modo simple del editor: no lo cambies a mano, se rehace solo.
[Command]
name = "sm_x"
command = x
time = 1

[Command]
name = "sm_y"
command = y
time = 1

[Command]
name = "sm_z"
command = z
time = 1

[Command]
name = "sm_a"
command = a
time = 1

[Command]
name = "sm_b"
command = b
time = 1

[Command]
name = "sm_c"
command = c
time = 1

[Command]
name = "sm_x_ad"
command = x
time = 1
buffer.time = 12

[Command]
name = "sm_y_ad"
command = y
time = 1
buffer.time = 12

[Command]
name = "sm_z_ad"
command = z
time = 1
buffer.time = 12

[Command]
name = "sm_a_ad"
command = a
time = 1
buffer.time = 12

[Command]
name = "sm_b_ad"
command = b
time = 1
buffer.time = 12

[Command]
name = "sm_c_ad"
command = c
time = 1
buffer.time = 12

[Command]
name = "sm_hd"
command = /$D
time = 1

[Command]
name = "sm_hf"
command = /$F
time = 1

[Command]
name = "sm_hold_F"
command = /F
time = 1

[Command]
name = "sm_hold_B"
command = /B
time = 1

[Command]
name = "sm_sp0_0"
command = ~D, DF, F, x
time = 20
buffer.time = 8

[Command]
name = "sm_sp0_1"
command = ~D, DF, F, y
time = 20
buffer.time = 8

[Command]
name = "sm_sp0_2"
command = ~D, DF, F, z
time = 20
buffer.time = 8

[Command]
name = "sm_sp1_0"
command = ~F, D, DF, a
time = 20
buffer.time = 8

[Command]
name = "sm_sp1_1"
command = ~F, D, DF, b
time = 20
buffer.time = 8

[Command]
name = "sm_sp1_2"
command = ~F, D, DF, c
time = 20
buffer.time = 8

[Command]
name = "sm_sp2_0"
command = ~D, DB, B, a
time = 20
buffer.time = 8

[Command]
name = "sm_sp2_1"
command = ~D, DB, B, b
time = 20
buffer.time = 8

[Command]
name = "sm_sp2_2"
command = ~D, DB, B, c
time = 20
buffer.time = 8

[Command]
name = "sm_sp3"
command = ~D, DF, F, D, DF, F, a
time = 30
buffer.time = 8

[Command]
name = "sm_sp3"
command = ~D, DF, F, D, DF, F, b
time = 30
buffer.time = 8

[Command]
name = "sm_sp3"
command = ~D, DF, F, D, DF, F, c
time = 30
buffer.time = 8
; <<< SIMPLE-MODE commands <<<

[Statedef -1]

; >>> SIMPLE-MODE moves >>>
; Esto lo escribe el modo simple del editor: no lo cambies a mano, se rehace solo.
[State -1, SM: Hōō Renkyaku]
type = ChangeState
value = 3300
triggerall = command = "sm_sp3"
triggerall = power >= 1000
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)
trigger3 = statetype != A
trigger3 = movecontact
trigger3 = stateno = 1000 || stateno = 1001 || stateno = 1002 || stateno = 1003 || stateno = 1100 || stateno = 1101 || stateno = 1102 || stateno = 1103 || stateno = 1200 || stateno = 1201 || stateno = 1202 || stateno = 1203

[State -1, SM: Hien (débil)]
type = ChangeState
value = 1000
triggerall = command = "sm_sp0_0"
triggerall = NumProjID(1000) = 0
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Hien (medio)]
type = ChangeState
value = 1001
triggerall = command = "sm_sp0_1"
triggerall = NumProjID(1000) = 0
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Hien (fuerte)]
type = ChangeState
value = 1002
triggerall = command = "sm_sp0_2"
triggerall = NumProjID(1000) = 0
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Shōten-kyaku (débil)]
type = ChangeState
value = 1100
triggerall = command = "sm_sp1_0"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Shōten-kyaku (medio)]
type = ChangeState
value = 1101
triggerall = command = "sm_sp1_1"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Shōten-kyaku (fuerte)]
type = ChangeState
value = 1102
triggerall = command = "sm_sp1_2"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Senpū-kyaku (débil)]
type = ChangeState
value = 1200
triggerall = command = "sm_sp2_0"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Senpū-kyaku (medio)]
type = ChangeState
value = 1201
triggerall = command = "sm_sp2_1"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Senpū-kyaku (fuerte)]
type = ChangeState
value = 1202
triggerall = command = "sm_sp2_2"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (StateNo = 201 || StateNo = 210 || StateNo = 230 || StateNo = 240 || StateNo = 400 || StateNo = 410 || StateNo = 430 || StateNo = 440 || StateNo = 600 || StateNo = 610 || StateNo = 630 || StateNo = 640)

[State -1, SM: Daño en combos largos]
type = AttackMulSet
trigger1 = 1
value = 1

[State -1, SM: Daño en combos largos 90%]
type = AttackMulSet
trigger1 = NumEnemy
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 3
value = 0.9

[State -1, SM: Daño en combos largos 80%]
type = AttackMulSet
trigger1 = NumEnemy
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 4
value = 0.8

[State -1, SM: Daño en combos largos 70%]
type = AttackMulSet
trigger1 = NumEnemy
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 5
value = 0.7

[State -1, SM: Daño en combos largos 60%]
type = AttackMulSet
trigger1 = NumEnemy
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 6
value = 0.6

[State -1, SM: Daño en combos largos 50%]
type = AttackMulSet
trigger1 = NumEnemy
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 7
value = 0.5

[State -1, SM: Agarre]
type = ChangeState
value = 800
triggerall = command = "sm_y"
triggerall = command = "sm_hf"
trigger1 = statetype = S
trigger1 = ctrl
trigger1 = p2bodydist X < 24
trigger1 = p2statetype != A
trigger1 = p2movetype != H

[State -1, SM: En el aire: Puño débil (x)]
type = ChangeState
value = 600
triggerall = command = "sm_x"
trigger1 = statetype = A
trigger1 = ctrl

[State -1, SM: En el aire: Puño medio (y)]
type = ChangeState
value = 610
triggerall = command = "sm_y"
trigger1 = statetype = A
trigger1 = ctrl

[State -1, SM: En el aire: Puño fuerte (z)]
type = ChangeState
value = 620
triggerall = command = "sm_z"
trigger1 = statetype = A
trigger1 = ctrl

[State -1, SM: En el aire: Patada débil (a)]
type = ChangeState
value = 630
triggerall = command = "sm_a"
trigger1 = statetype = A
trigger1 = ctrl

[State -1, SM: En el aire: Patada media (b)]
type = ChangeState
value = 640
triggerall = command = "sm_b"
trigger1 = statetype = A
trigger1 = ctrl

[State -1, SM: En el aire: Patada fuerte (c)]
type = ChangeState
value = 650
triggerall = command = "sm_c"
trigger1 = statetype = A
trigger1 = ctrl

[State -1, SM: Agachado: Puño débil (x)]
type = ChangeState
value = 400
triggerall = command = "sm_x"
triggerall = command = "sm_hd"
trigger1 = statetype = C
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = StateNo = 400

[State -1, SM: Agachado: Puño medio (y)]
type = ChangeState
value = 410
triggerall = command = "sm_y"
triggerall = command = "sm_hd"
trigger1 = statetype = C
trigger1 = ctrl

[State -1, SM: Agachado: Puño fuerte (z)]
type = ChangeState
value = 420
triggerall = command = "sm_z"
triggerall = command = "sm_hd"
trigger1 = statetype = C
trigger1 = ctrl

[State -1, SM: Agachado: Patada débil (a)]
type = ChangeState
value = 430
triggerall = command = "sm_a"
triggerall = command = "sm_hd"
trigger1 = statetype = C
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = StateNo = 430

[State -1, SM: Agachado: Patada media (b)]
type = ChangeState
value = 440
triggerall = command = "sm_b"
triggerall = command = "sm_hd"
trigger1 = statetype = C
trigger1 = ctrl

[State -1, SM: Agachado: Patada fuerte (c)]
type = ChangeState
value = 450
triggerall = command = "sm_c"
triggerall = command = "sm_hd"
trigger1 = statetype = C
trigger1 = ctrl

[State -1, SM: De pie: Patada fuerte (c)]
type = ChangeState
value = 250
triggerall = command = "sm_c"
triggerall = command != "sm_hd"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, SM: De pie: Patada media (b)]
type = ChangeState
value = 240
triggerall = command = "sm_b"
triggerall = command != "sm_hd"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, SM: De pie: Patada débil (a)]
type = ChangeState
value = 230
triggerall = command = "sm_a"
triggerall = command != "sm_hd"
trigger1 = statetype = S
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = StateNo = 230

[State -1, SM: De pie: Puño fuerte (z)]
type = ChangeState
value = 220
triggerall = command = "sm_z"
triggerall = command != "sm_hd"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, SM: De pie: Puño medio (y)]
type = ChangeState
value = 210
triggerall = command = "sm_y"
triggerall = command != "sm_hd"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, SM: De pie: Puño débil (x)]
type = ChangeState
value = 201
triggerall = command = "sm_x"
triggerall = command != "sm_hd"
trigger1 = statetype = S
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = StateNo = 201
; <<< SIMPLE-MODE moves <<<


[State -1, Correr]
type = ChangeState
value = 100
trigger1 = command = "FF"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, Salto hacia atrás]
type = ChangeState
value = 105
trigger1 = command = "BB"
trigger1 = statetype = S
trigger1 = ctrl

[State -1, Golpe]
triggerall = 0 ; SIMPLE-MODE: off
type = ChangeState
value = 200
triggerall = command = "a"
trigger1 = statetype = S
trigger1 = ctrl
