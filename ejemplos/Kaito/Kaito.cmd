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
name = "sm_brk0"
command = x+a
time = 1

[Command]
name = "sm_brk1"
command = y+b
time = 1

[Command]
name = "sm_brk2"
command = z+c
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
command = ~F, D, DF, x
time = 20
buffer.time = 8

[Command]
name = "sm_sp1_1"
command = ~F, D, DF, y
time = 20
buffer.time = 8

[Command]
name = "sm_sp1_2"
command = ~F, D, DF, z
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
command = ~D, DF, F, D, DF, F, x
time = 30
buffer.time = 8

[Command]
name = "sm_sp3"
command = ~D, DF, F, D, DF, F, y
time = 30
buffer.time = 8

[Command]
name = "sm_sp3"
command = ~D, DF, F, D, DF, F, z
time = 30
buffer.time = 8

[Command]
name = "sm_sp4"
command = ~F, D, DF, z
time = 30
buffer.time = 8
; <<< SIMPLE-MODE commands <<<

[Statedef -1]

; >>> SIMPLE-MODE moves >>>
; Esto lo escribe el modo simple del editor: no lo cambies a mano, se rehace solo.
[State -1, SM: Tatsu-geri (Remate)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 4020
triggerall = command = "sm_sp2_2"
trigger1 = statetype != A
trigger1 = movecontact
trigger1 = (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0)
trigger2 = statetype != A
trigger2 = ctrl
trigger2 = GameTime - Map(sm_adt) <= 20
trigger2 = NumEnemy
trigger2 = EnemyNear, MoveType = H

[State -1, SM: Ryūjin Remate (Remate)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 3900
triggerall = command = "sm_sp4"
trigger1 = statetype != A
trigger1 = movecontact
trigger1 = (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0)
trigger2 = statetype != A
trigger2 = ctrl
trigger2 = GameTime - Map(sm_adt) <= 20
trigger2 = NumEnemy
trigger2 = EnemyNear, MoveType = H

[State -1, SM: Rengeki]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 3300
triggerall = command = "sm_sp3"
triggerall = power >= 1000
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))
trigger3 = statetype != A
trigger3 = movecontact
trigger3 = stateno = 1000 || stateno = 1001 || stateno = 1002 || stateno = 1003 || stateno = 1100 || stateno = 1101 || stateno = 1102 || stateno = 1103 || stateno = 1200 || stateno = 1201 || stateno = 1202 || stateno = 1203

[State -1, SM: Kikō-ha (débil)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1000
triggerall = command = "sm_sp0_0"
triggerall = NumProjID(1000) = 0
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Kikō-ha (medio)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1001
triggerall = command = "sm_sp0_1"
triggerall = NumProjID(1000) = 0
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Kikō-ha (fuerte)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1002
triggerall = command = "sm_sp0_2"
triggerall = NumProjID(1000) = 0
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Ryūjin (débil)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1100
triggerall = command = "sm_sp1_0"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Ryūjin (medio)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1101
triggerall = command = "sm_sp1_1"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Ryūjin (fuerte)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1102
triggerall = command = "sm_sp1_2"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Tatsu-geri (débil)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1200
triggerall = command = "sm_sp2_0"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Tatsu-geri (medio)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1201
triggerall = command = "sm_sp2_1"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Tatsu-geri (fuerte)]
type = ChangeState
triggerall = Map(sm_end) = 0
value = 1202
triggerall = command = "sm_sp2_2"
trigger1 = statetype != A
trigger1 = ctrl
trigger2 = statetype != A
trigger2 = movecontact
trigger2 = (stateno = [200, 699] || (StateNo = 750 && Anim = 230 && AnimElemTime(2) > 0) || (StateNo = 751 && Anim = 240 && AnimElemTime(2) > 0) || (StateNo = 752 && Anim = 250 && AnimElemTime(2) > 0))

[State -1, SM: Remate: cierra el combo]
type = MapSet
trigger1 = movecontact
trigger1 = StateNo = 3900 || StateNo = 4020
map = "sm_end"
value = 1

[State -1, SM: Remate: fin del combo]
type = MapSet
map = "sm_end"
value = 0
trigger1 = !NumEnemy
trigger2 = NumEnemy
trigger2 = EnemyNear, MoveType != H

[State -1, SM: Autodoble: fin del combo]
type = MapSet
map = "sm_adn"
value = 0
trigger1 = !NumEnemy
trigger2 = NumEnemy
trigger2 = EnemyNear, MoveType != H

[State -1, SM: Autodoble (Débil): reloj]
type = MapSet
trigger1 = movehit
trigger1 = StateNo = 610 || StateNo = 640 || StateNo = 1001 || StateNo = 1101 || StateNo = 1201
map = "sm_ad0t"
value = GameTime

[State -1, SM: Autodoble (Medio): reloj]
type = MapSet
trigger1 = movehit
trigger1 = StateNo = 620 || StateNo = 650 || StateNo = 1002 || StateNo = 1003 || StateNo = 1102 || StateNo = 1103 || StateNo = 1202 || StateNo = 1203 || StateNo = 3300
map = "sm_ad1t"
value = GameTime

[State -1, SM: Autodoble (Fuerte): reloj]
type = MapSet
trigger1 = movehit
trigger1 = StateNo = 600 || StateNo = 630 || StateNo = 1000 || StateNo = 1100 || StateNo = 1200
map = "sm_ad2t"
value = GameTime

[State -1, SM: Autodoble: reloj]
type = MapSet
trigger1 = StateNo = 750 || StateNo = 751 || StateNo = 752
map = "sm_adt"
value = GameTime

[State -1, SM: Combo breaker (Débil)]
type = ChangeState
value = 770
triggerall = command = "sm_brk0"
triggerall = Alive
triggerall = movetype = H
triggerall = stateno = [5000, 5099]
triggerall = GetHitVar(hitcount) >= 2
triggerall = Map(sm_brklock) <= 0
trigger1 = GetHitVar(animtype) = 0

[State -1, SM: Combo breaker (Medio)]
type = ChangeState
value = 770
triggerall = command = "sm_brk1"
triggerall = Alive
triggerall = movetype = H
triggerall = stateno = [5000, 5099]
triggerall = GetHitVar(hitcount) >= 2
triggerall = Map(sm_brklock) <= 0
trigger1 = GetHitVar(animtype) = 1

[State -1, SM: Combo breaker (Fuerte)]
type = ChangeState
value = 770
triggerall = command = "sm_brk2"
triggerall = Alive
triggerall = movetype = H
triggerall = stateno = [5000, 5099]
triggerall = GetHitVar(hitcount) >= 2
triggerall = Map(sm_brklock) <= 0
trigger1 = GetHitVar(animtype) >= 2

[State -1, SM: Combo breaker: falló]
type = MapSet
triggerall = Alive
triggerall = movetype = H
triggerall = stateno = [5000, 5099]
triggerall = GetHitVar(hitcount) >= 2
triggerall = Map(sm_brklock) <= 0
trigger1 = (command = "sm_brk0" && !(GetHitVar(animtype) = 0)) || (command = "sm_brk1" && !(GetHitVar(animtype) = 1)) || (command = "sm_brk2" && !(GetHitVar(animtype) >= 2))
map = "sm_brklock"
value = 180

[State -1, SM: Combo breaker: bloqueado]
type = MapAdd
trigger1 = Map(sm_brklock) > 0
map = "sm_brklock"
value = -1

[State -1, SM: Combo breaker: se acabó el combo]
type = MapSet
trigger1 = Map(sm_brklock) > 0
trigger1 = movetype != H
map = "sm_brklock"
value = 0

[State -1, SM: Combo breaker: se ve bloqueado]
type = PalFX
trigger1 = Map(sm_brklock) > 0
time = 2
add = 40, 0, 0
mul = 256, 170, 170

[State -1, SM: Autodoble (Débil)]
type = ChangeState
value = 750
triggerall = command = "sm_x_ad" || command = "sm_a_ad"
triggerall = statetype != A
triggerall = Map(sm_end) = 0
triggerall = Map(sm_adn) < 4
triggerall = NumEnemy
triggerall = EnemyNear, StateType != A
triggerall = EnemyNear, StateNo = [5000, 5019]
trigger1 = movehit
trigger1 = StateNo = 1001 || (StateNo = 1101 && AnimElemTime(2) > 0) || (StateNo = 1201 && AnimElemTime(2) > 0) || StateNo = 610 || StateNo = 640
trigger2 = ctrl
trigger2 = GameTime - Map(sm_ad0t) <= 20
trigger2 = NumEnemy
trigger2 = EnemyNear, MoveType = H
trigger3 = (ProjHitTime(1000) >= 0 && ProjHitTime(1000) <= 20)
trigger3 = ctrl || StateNo = 1001
trigger3 = NumEnemy
trigger3 = EnemyNear, MoveType = H

[State -1, SM: Autodoble (Medio)]
type = ChangeState
value = 751
triggerall = command = "sm_y_ad" || command = "sm_b_ad"
triggerall = statetype != A
triggerall = Map(sm_end) = 0
triggerall = Map(sm_adn) < 4
triggerall = NumEnemy
triggerall = EnemyNear, StateType != A
triggerall = EnemyNear, StateNo = [5000, 5019]
trigger1 = movehit
trigger1 = StateNo = 1002 || StateNo = 1003 || (StateNo = 1102 && AnimElemTime(2) > 0) || (StateNo = 1103 && AnimElemTime(2) > 0) || (StateNo = 1202 && AnimElemTime(2) > 0) || (StateNo = 1203 && AnimElemTime(2) > 0) || (StateNo = 3300 && AnimElemTime(2) > 20) || StateNo = 620 || StateNo = 650
trigger2 = ctrl
trigger2 = GameTime - Map(sm_ad1t) <= 20
trigger2 = NumEnemy
trigger2 = EnemyNear, MoveType = H
trigger3 = (ProjHitTime(1000) >= 0 && ProjHitTime(1000) <= 20)
trigger3 = ctrl || StateNo = 1002 || StateNo = 1003
trigger3 = NumEnemy
trigger3 = EnemyNear, MoveType = H

[State -1, SM: Autodoble (Fuerte)]
type = ChangeState
value = 752
triggerall = command = "sm_z_ad" || command = "sm_c_ad"
triggerall = statetype != A
triggerall = Map(sm_end) = 0
triggerall = Map(sm_adn) < 4
triggerall = NumEnemy
triggerall = EnemyNear, StateType != A
triggerall = EnemyNear, StateNo = [5000, 5019]
trigger1 = movehit
trigger1 = StateNo = 1000 || (StateNo = 1100 && AnimElemTime(2) > 0) || (StateNo = 1200 && AnimElemTime(2) > 0) || StateNo = 600 || StateNo = 630
trigger2 = ctrl
trigger2 = GameTime - Map(sm_ad2t) <= 20
trigger2 = NumEnemy
trigger2 = EnemyNear, MoveType = H
trigger3 = (ProjHitTime(1000) >= 0 && ProjHitTime(1000) <= 20)
trigger3 = ctrl || StateNo = 1000
trigger3 = NumEnemy
trigger3 = EnemyNear, MoveType = H

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
