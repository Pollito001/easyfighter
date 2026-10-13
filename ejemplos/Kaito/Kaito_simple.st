; Movimientos del modo simple del editor. Este archivo se rehace solo cada vez que cambias algo en el modo simple: no lo edites a mano (los cambios se perderían).

; De pie: Puño débil (x)
[Statedef 201]
type = S
movetype = A
physics = S
juggle = 1
velset = 0, 0
ctrl = 0
anim = 201
poweradd = 10
sprpriority = 2

[State 201, Golpe]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 25, 0
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
ground.hittime = 12
sparkxy = -10, -149
ground.velocity = -6
air.velocity = -3.6, -6

[State 201, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; De pie: Puño medio (y)
[Statedef 210]
type = S
movetype = A
physics = S
juggle = 1
velset = 0, 0
ctrl = 0
anim = 210
poweradd = 18
sprpriority = 2

[State 210, Golpe]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 40, 0
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
ground.hittime = 15
sparkxy = -10, -145
ground.velocity = -9
air.velocity = -5.4, -6

[State 210, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; De pie: Puño fuerte (z)
[Statedef 220]
type = S
movetype = A
physics = S
juggle = 1
velset = 0, 0
ctrl = 0
anim = 220
poweradd = 25
sprpriority = 2

[State 220, Golpe]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 60, 0
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
ground.hittime = 18
sparkxy = -10, -146
ground.velocity = -12
air.velocity = -7.2, -6

[State 220, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; De pie: Patada débil (a)
[Statedef 230]
type = S
movetype = A
physics = S
juggle = 1
velset = 0, 0
ctrl = 0
anim = 230
poweradd = 10
sprpriority = 2

[State 230, Golpe]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 28, 0
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
ground.hittime = 12
sparkxy = -10, -45
ground.velocity = -6
air.velocity = -3.6, -6

[State 230, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; De pie: Patada media (b)
[Statedef 240]
type = S
movetype = A
physics = S
juggle = 1
velset = 0, 0
ctrl = 0
anim = 240
poweradd = 18
sprpriority = 2

[State 240, Golpe]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 45, 0
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
ground.hittime = 15
sparkxy = -10, -96
ground.velocity = -9
air.velocity = -5.4, -6

[State 240, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; De pie: Patada fuerte (c)
[Statedef 250]
type = S
movetype = A
physics = S
juggle = 1
velset = 0, 0
ctrl = 0
anim = 250
poweradd = 25
sprpriority = 2

[State 250, Golpe]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 65, 0
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
ground.hittime = 18
sparkxy = -10, -153
ground.velocity = -12
air.velocity = -7.2, -6

[State 250, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Agachado: Puño débil (x)
[Statedef 400]
type = C
movetype = A
physics = C
juggle = 1
velset = 0, 0
ctrl = 0
anim = 400
poweradd = 10
sprpriority = 2

[State 400, Golpe]
type = HitDef
trigger1 = Time = 0
attr = C, NA
damage = 25, 0
animtype = Light
guardflag = L
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = Low
ground.slidetime = 8
ground.hittime = 12
sparkxy = -10, -99
ground.velocity = -6
air.velocity = -3.6, -6

[State 400, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 11
ctrl = 1

;---------------------------------------------------------------------------
; Agachado: Puño medio (y)
[Statedef 410]
type = C
movetype = A
physics = C
juggle = 1
velset = 0, 0
ctrl = 0
anim = 410
poweradd = 18
sprpriority = 2

[State 410, Golpe]
type = HitDef
trigger1 = Time = 0
attr = C, NA
damage = 40, 0
animtype = Medium
guardflag = L
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = Low
ground.slidetime = 11
ground.hittime = 15
sparkxy = -10, -102
ground.velocity = -9
air.velocity = -5.4, -6

[State 410, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 11
ctrl = 1

;---------------------------------------------------------------------------
; Agachado: Puño fuerte (z)
[Statedef 420]
type = C
movetype = A
physics = C
juggle = 1
velset = 0, 0
ctrl = 0
anim = 420
poweradd = 25
sprpriority = 2

[State 420, Golpe]
type = HitDef
trigger1 = Time = 0
attr = C, NA
damage = 60, 0
animtype = Heavy
guardflag = L
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = Low
ground.slidetime = 14
ground.hittime = 18
sparkxy = -10, -124
ground.velocity = -12
air.velocity = -7.2, -6

[State 420, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 11
ctrl = 1

;---------------------------------------------------------------------------
; Agachado: Patada débil (a)
[Statedef 430]
type = C
movetype = A
physics = C
juggle = 1
velset = 0, 0
ctrl = 0
anim = 430
poweradd = 10
sprpriority = 2

[State 430, Golpe]
type = HitDef
trigger1 = Time = 0
attr = C, NA
damage = 28, 0
animtype = Light
guardflag = L
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = Low
ground.slidetime = 8
ground.hittime = 12
sparkxy = -10, -50
ground.velocity = -6
air.velocity = -3.6, -6

[State 430, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 11
ctrl = 1

;---------------------------------------------------------------------------
; Agachado: Patada media (b)
[Statedef 440]
type = C
movetype = A
physics = C
juggle = 1
velset = 0, 0
ctrl = 0
anim = 440
poweradd = 18
sprpriority = 2

[State 440, Golpe]
type = HitDef
trigger1 = Time = 0
attr = C, NA
damage = 45, 0
animtype = Medium
guardflag = L
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = Low
ground.slidetime = 11
ground.hittime = 15
sparkxy = -10, -60
ground.velocity = -9
air.velocity = -5.4, -6

[State 440, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 11
ctrl = 1

;---------------------------------------------------------------------------
; Agachado: Patada fuerte (c)
[Statedef 450]
type = C
movetype = A
physics = C
juggle = 1
velset = 0, 0
ctrl = 0
anim = 450
poweradd = 25
sprpriority = 2

[State 450, Golpe]
type = HitDef
trigger1 = Time = 0
attr = C, NA
damage = 65, 0
animtype = Heavy
guardflag = L
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = Trip
ground.slidetime = 14
ground.hittime = 18
sparkxy = -10, -71
ground.velocity = -9.6, -13
air.velocity = -8.4, -12
fall = 1
air.fall = 1
fall.recover = 0

[State 450, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 11
ctrl = 1

;---------------------------------------------------------------------------
; En el aire: Puño débil (x)
[Statedef 600]
type = A
movetype = A
physics = A
juggle = 2
ctrl = 0
anim = 600
poweradd = 10
sprpriority = 2

[State 600, Golpe]
type = HitDef
trigger1 = Time = 0
attr = A, NA
damage = 25, 0
animtype = Light
guardflag = HA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
ground.hittime = 28
sparkxy = -10, -150
ground.velocity = -6
air.velocity = -3.6, -6
air.hittime = 28

;---------------------------------------------------------------------------
; En el aire: Puño medio (y)
[Statedef 610]
type = A
movetype = A
physics = A
juggle = 2
ctrl = 0
anim = 610
poweradd = 18
sprpriority = 2

[State 610, Golpe]
type = HitDef
trigger1 = Time = 0
attr = A, NA
damage = 40, 0
animtype = Medium
guardflag = HA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
ground.hittime = 28
sparkxy = -10, -154
ground.velocity = -9
air.velocity = -5.4, -6
air.hittime = 28

;---------------------------------------------------------------------------
; En el aire: Puño fuerte (z)
[Statedef 620]
type = A
movetype = A
physics = A
juggle = 2
ctrl = 0
anim = 620
poweradd = 25
sprpriority = 2

[State 620, Golpe]
type = HitDef
trigger1 = Time = 0
attr = A, NA
damage = 60, 0
animtype = Heavy
guardflag = HA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
ground.hittime = 28
sparkxy = -10, -164
ground.velocity = -12
air.velocity = -7.2, -6
air.hittime = 28

;---------------------------------------------------------------------------
; En el aire: Patada débil (a)
[Statedef 630]
type = A
movetype = A
physics = A
juggle = 2
ctrl = 0
anim = 630
poweradd = 10
sprpriority = 2

[State 630, Golpe]
type = HitDef
trigger1 = Time = 0
attr = A, NA
damage = 28, 0
animtype = Light
guardflag = HA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
ground.hittime = 28
sparkxy = -10, -136
ground.velocity = -6
air.velocity = -3.6, -6
air.hittime = 28

;---------------------------------------------------------------------------
; En el aire: Patada media (b)
[Statedef 640]
type = A
movetype = A
physics = A
juggle = 2
ctrl = 0
anim = 640
poweradd = 18
sprpriority = 2

[State 640, Golpe]
type = HitDef
trigger1 = Time = 0
attr = A, NA
damage = 45, 0
animtype = Medium
guardflag = HA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
ground.hittime = 28
sparkxy = -10, -98
ground.velocity = -9
air.velocity = -5.4, -6
air.hittime = 28

;---------------------------------------------------------------------------
; En el aire: Patada fuerte (c)
[Statedef 650]
type = A
movetype = A
physics = A
juggle = 2
ctrl = 0
anim = 650
poweradd = 25
sprpriority = 2

[State 650, Golpe]
type = HitDef
trigger1 = Time = 0
attr = A, NA
damage = 65, 0
animtype = Heavy
guardflag = HA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
ground.hittime = 28
sparkxy = -10, -109
ground.velocity = -12
air.velocity = -7.2, -6
air.hittime = 28

;---------------------------------------------------------------------------
; Agarre
[Statedef 800]
type = S
movetype = A
physics = S
juggle = 0
velset = 0, 0
ctrl = 0
anim = 800
sprpriority = 2

[State 800, Agarrar]
type = HitDef
trigger1 = Time = 0
attr = S, NT
hitflag = M-
priority = 1, Miss
sparkno = -1
p1sprpriority = 1
p2sprpriority = 0
p1facing = 1
p2facing = 1
p1stateno = 810
p2stateno = 820
guard.dist = 0
fall = 1

[State 800, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

; Agarre (lo tiene agarrado)
[Statedef 810]
type = S
movetype = A
physics = N
velset = 0, 0
ctrl = 0
anim = 810
poweradd = 40
sprpriority = 2

[State 810, Sujetar]
type = TargetBind
trigger1 = AnimElemTime(2) < 0
pos = 60, 0

[State 810, Daño]
type = TargetLifeAdd
trigger1 = AnimElem = 2
value = -80

[State 810, Lanzar]
type = TargetState
trigger1 = AnimElem = 2
value = 821

[State 810, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = 0
ctrl = 1

; Agarre (el rival, agarrado)
[Statedef 820]
type = A
movetype = H
physics = N
velset = 0, 0

[State 820, Animación]
type = ChangeAnim
trigger1 = Time = 0
value = 5000

; Agarre (el rival, lanzado)
[Statedef 821]
type = A
movetype = H
physics = N

[State 821, Volar]
type = VelSet
trigger1 = Time = 0
x = -8
y = -14

[State 821, Caer]
type = HitFallSet
trigger1 = Time = 0
value = 1

[State 821, Caer 2]
type = SelfState
trigger1 = Time = 0
value = 5050

;---------------------------------------------------------------------------
; Combo breaker
[Statedef 770]
type = U
movetype = A
physics = N
juggle = 0
velset = 0, 0
ctrl = 0
anim = 201
sprpriority = 2

[State 770, Invencible]
type = NotHitBy
trigger1 = Time = 0
value = SCA
time = 30

[State 770, Destello]
type = PalFX
trigger1 = Time = 0
time = 12
add = 160, 160, 255
mul = 256, 256, 256

[State 770, Temblor]
type = EnvShake
trigger1 = Time = 0
time = 12
ampl = 4

[State 770, Empujar]
type = HitDef
trigger1 = Time = 0
attr = S, NA
damage = 0
animtype = Heavy
hitflag = MAFD
priority = 7, Hit
pausetime = 0, 12
sparkno = 2
hitsound = 5, 2
ground.type = High
ground.slidetime = 12
ground.hittime = 16
ground.velocity = -14, -8
air.velocity = -14, -8
fall = 1
air.fall = 1
fall.recover = 1
sparkxy = -10, -149

[State 770, Fin]
type = ChangeState
trigger1 = AnimTime = 0
value = ifelse(Pos Y < -1, 50, 0)
ctrl = 1

;---------------------------------------------------------------------------
; Kikō-ha (débil)
[Statedef 1000]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1000
poweradd = 40
sprpriority = 2

[State 1000, Proyectil]
type = Projectile
trigger1 = AnimElem = 3
projid = 1000
projanim = 1050
projremove = 1
projhits = 1
projmisstime = 6
velocity = 7.5, -0
accel = 0, -0
offset = 96, -136
projpriority = 1
projsprpriority = 3
projremovetime = -1
projscale = ifelse(const(size.proj.doscale), 1, const(size.xscale)), ifelse(const(size.proj.doscale), 1, const(size.yscale))
projhitanim = 1060
projremanim = 1060
attr = S, SP
damage = 48, 6
animtype = Light
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 12, 12
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 56
air.hittime = 56
ground.velocity = -9
air.velocity = -5.4, -6

[State 1000, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Kikō-ha (medio)
[Statedef 1001]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1000
poweradd = 40
sprpriority = 2

[State 1001, Proyectil]
type = Projectile
trigger1 = AnimElem = 3
projid = 1000
projanim = 1050
projremove = 1
projhits = 1
projmisstime = 6
velocity = 10, -0
accel = 0, -0
offset = 96, -136
projpriority = 1
projsprpriority = 3
projremovetime = -1
projscale = ifelse(const(size.proj.doscale), 1, const(size.xscale)), ifelse(const(size.proj.doscale), 1, const(size.yscale))
projhitanim = 1060
projremanim = 1060
attr = S, SP
damage = 60, 7
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 12, 12
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 56
air.hittime = 56
ground.velocity = -9
air.velocity = -5.4, -6

[State 1001, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Kikō-ha (fuerte)
[Statedef 1002]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1000
poweradd = 40
sprpriority = 2

[State 1002, Proyectil]
type = Projectile
trigger1 = AnimElem = 3
projid = 1000
projanim = 1050
projremove = 1
projhits = 1
projmisstime = 6
velocity = 12.5, -0
accel = 0, -0
offset = 96, -136
projpriority = 1
projsprpriority = 3
projremovetime = -1
projscale = ifelse(const(size.proj.doscale), 1, const(size.xscale)), ifelse(const(size.proj.doscale), 1, const(size.yscale))
projhitanim = 1060
projremanim = 1060
attr = S, SP
damage = 72, 9
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 12, 12
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 56
air.hittime = 56
ground.velocity = -9
air.velocity = -5.4, -6

[State 1002, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Ryūjin (débil)
[Statedef 1100]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1100
poweradd = 40
sprpriority = 2

[State 1100, Invencible]
type = NotHitBy
trigger1 = Time = 0
value = SCA
time = 4

[State 1100, Golpe]
type = HitDef
trigger1 = AnimElem = 2
attr = S, SA
damage = 64, 8
animtype = Light
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 44
air.hittime = 44
sparkxy = -10, -192
ground.velocity = -7.2, -13
air.velocity = -6.3, -12
fall = 1
air.fall = 1
fall.recover = 1

[State 1100, Despegar]
type = StateTypeSet
trigger1 = AnimElem = 1
statetype = A
physics = A

[State 1100, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 1
x = 2.7
y = -14.45

[State 1100, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Ryūjin (medio)
[Statedef 1101]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1100
poweradd = 40
sprpriority = 2

[State 1101, Invencible]
type = NotHitBy
trigger1 = Time = 0
value = SCA
time = 4

[State 1101, Golpe]
type = HitDef
trigger1 = AnimElem = 2
attr = S, SA
damage = 80, 10
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 44
air.hittime = 44
sparkxy = -10, -192
ground.velocity = -7.2, -13
air.velocity = -6.3, -12
fall = 1
air.fall = 1
fall.recover = 1

[State 1101, Despegar]
type = StateTypeSet
trigger1 = AnimElem = 1
statetype = A
physics = A

[State 1101, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 1
x = 3.6
y = -17

[State 1101, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Ryūjin (fuerte)
[Statedef 1102]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1100
poweradd = 40
sprpriority = 2

[State 1102, Invencible]
type = NotHitBy
trigger1 = Time = 0
value = SCA
time = 4

[State 1102, Golpe]
type = HitDef
trigger1 = AnimElem = 2
attr = S, SA
damage = 96, 12
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 44
air.hittime = 44
sparkxy = -10, -192
ground.velocity = -7.2, -13
air.velocity = -6.3, -12
fall = 1
air.fall = 1
fall.recover = 1

[State 1102, Despegar]
type = StateTypeSet
trigger1 = AnimElem = 1
statetype = A
physics = A

[State 1102, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 1
x = 4.5
y = -19.55

[State 1102, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Tatsu-geri (débil)
[Statedef 1200]
type = S
movetype = A
physics = N
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1200
poweradd = 40
sprpriority = 2

[State 1200, Golpe]
type = HitDef
trigger1 = AnimElem = 2
attr = S, SA
damage = 56, 7
animtype = Light
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 34
air.hittime = 34
sparkxy = -10, -60
ground.velocity = -9
air.velocity = -5.4, -6

[State 1200, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 1
x = 9.75

[State 1200, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 5
x = 0

[State 1200, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Tatsu-geri (medio)
[Statedef 1201]
type = S
movetype = A
physics = N
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1200
poweradd = 40
sprpriority = 2

[State 1201, Golpe]
type = HitDef
trigger1 = AnimElem = 2
attr = S, SA
damage = 70, 8
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 34
air.hittime = 34
sparkxy = -10, -60
ground.velocity = -9
air.velocity = -5.4, -6

[State 1201, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 1
x = 13

[State 1201, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 5
x = 0

[State 1201, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Tatsu-geri (fuerte)
[Statedef 1202]
type = S
movetype = A
physics = N
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1200
poweradd = 40
sprpriority = 2

[State 1202, Golpe]
type = HitDef
trigger1 = AnimElem = 2
attr = S, SA
damage = 84, 10
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 34
air.hittime = 34
sparkxy = -10, -60
ground.velocity = -9
air.velocity = -5.4, -6

[State 1202, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 1
x = 16.25

[State 1202, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 5
x = 0

[State 1202, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Rengeki
[Statedef 3300]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 3300
poweradd = -1000
sprpriority = 2

[State 3300, Golpe]
type = HitDef
trigger1 = AnimElemTime(2) >= 0
trigger1 = (AnimElemTime(2) % 5) = 0
trigger1 = AnimElemTime(2) < 25
attr = S, HA
damage = 44, 5
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
ground.hittime = 30
air.hittime = 30
sparkxy = -10, -147
ground.velocity = -1.2
air.velocity = -0.72, -6

[State 3300, Pausa con destello]
type = SuperPause
trigger1 = AnimElem = 1
time = 30
movetime = 0
darken = 1

[State 3300, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Ryūjin Remate (Remate)
[Statedef 3900]
type = S
movetype = A
physics = S
velset = 0, 0
juggle = 4
ctrl = 0
anim = 3900
poweradd = 40
sprpriority = 2

[State 3900, Golpe]
type = HitDef
trigger1 = AnimElem = 3
attr = S, SA
damage = 117, 11
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 16
sparkxy = -10, -148
ground.velocity = -9, -12
air.velocity = -9, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 3900, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Autodoble (Débil)
[Statedef 750]
type = S
movetype = A
physics = S
juggle = 0
velset = 0, 0
ctrl = 0
anim = 201
poweradd = 15
sprpriority = 2

[State 750, Cuenta de autodobles]
type = MapAdd
trigger1 = Time = 0
map = "sm_adn"
value = 1

[State 750, Correr hasta el rival]
type = ChangeAnim
trigger1 = Time = 0
trigger1 = P2BodyDist X > 60
value = 100

[State 750, Correr hasta el rival (2)]
type = VelSet
trigger1 = Anim = 100
x = 16

[State 750, Llegó]
type = ChangeAnim
trigger1 = Anim = 100
trigger1 = P2BodyDist X <= 30 || Time >= 45
value = 201

[State 750, Llegó (2)]
type = VelSet
trigger1 = Anim = 201
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
x = 0

[State 750, Acercarse]
type = VelSet
trigger1 = Time = 0
x = ifelse(P2BodyDist X > 60, 16, ifelse(P2BodyDist X > 20, (P2BodyDist X - 20) / 5.0, 0))

[State 750, Golpe 1]
type = HitDef
trigger1 = Anim = 201
trigger1 = AnimElemTime(1) = 0
trigger1 = EnemyNear, MoveType != H
trigger2 = Anim = 201
trigger2 = AnimElemTime(1) = 0
trigger2 = EnemyNear, GetHitVar(hitcount) < 16
attr = S, NA
damage = 15, 0
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
sparkxy = -10, -149
ground.hittime = 15
air.hittime = 15
ground.velocity = 0
air.velocity = 0, -5

[State 750, Golpe 1 (pasó del límite)]
type = HitDef
trigger1 = Anim = 201
trigger1 = AnimElemTime(1) = 0
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 16
attr = S, NA
damage = 15, 0
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
sparkxy = -10, -149
ground.hittime = 15
air.hittime = 15
ground.velocity = -12, -10
air.velocity = -12, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 750, Golpe 2: animación]
type = ChangeAnim
trigger1 = Anim = 201
trigger1 = AnimTime = 0
value = 230

[State 750, Acercarse 2]
type = VelSet
trigger1 = Anim = 230
trigger1 = AnimElemTime(1) = 0
x = ifelse(P2BodyDist X > 60, 16, ifelse(P2BodyDist X > 20, (P2BodyDist X - 20) / 5.0, 0))

[State 750, Golpe 2 (último autodoble del combo)]
type = HitDef
trigger1 = Anim = 230
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) >= 4
attr = S, NA
damage = 15, 0
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
sparkxy = -10, -45
ground.hittime = 40
air.hittime = 40
ground.velocity = -7.2, -12
air.velocity = -7.2, -12
fall = 1
air.fall = 1
fall.recover = 0

[State 750, Golpe 2]
type = HitDef
trigger1 = Anim = 230
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) < 4
trigger1 = EnemyNear, MoveType != H
trigger2 = Anim = 230
trigger2 = AnimElemTime(1) = 0
trigger2 = Time > 0
trigger2 = Map(sm_adn) < 4
trigger2 = EnemyNear, GetHitVar(hitcount) < 16
attr = S, NA
damage = 15, 0
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
sparkxy = -10, -45
ground.hittime = 40
air.hittime = 40
ground.velocity = 0
air.velocity = 0, -5

[State 750, Golpe 2 (pasó del límite)]
type = HitDef
trigger1 = Anim = 230
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) < 4
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 16
attr = S, NA
damage = 15, 0
animtype = Light
guardflag = MA
hitflag = MAF
priority = 3, Hit
pausetime = 8, 8
sparkno = 0
guard.sparkno = 40
hitsound = 5, 0
guardsound = 6, 0
ground.type = High
ground.slidetime = 8
sparkxy = -10, -45
ground.hittime = 40
air.hittime = 40
ground.velocity = -12, -10
air.velocity = -12, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 750, Fin]
type = ChangeState
trigger1 = Anim = 230
trigger1 = AnimTime = 0
trigger1 = Time > 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Autodoble (Medio)
[Statedef 751]
type = S
movetype = A
physics = S
juggle = 0
velset = 0, 0
ctrl = 0
anim = 210
poweradd = 15
sprpriority = 2

[State 751, Cuenta de autodobles]
type = MapAdd
trigger1 = Time = 0
map = "sm_adn"
value = 1

[State 751, Correr hasta el rival]
type = ChangeAnim
trigger1 = Time = 0
trigger1 = P2BodyDist X > 60
value = 100

[State 751, Correr hasta el rival (2)]
type = VelSet
trigger1 = Anim = 100
x = 16

[State 751, Llegó]
type = ChangeAnim
trigger1 = Anim = 100
trigger1 = P2BodyDist X <= 30 || Time >= 45
value = 210

[State 751, Llegó (2)]
type = VelSet
trigger1 = Anim = 210
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
x = 0

[State 751, Acercarse]
type = VelSet
trigger1 = Time = 0
x = ifelse(P2BodyDist X > 60, 16, ifelse(P2BodyDist X > 20, (P2BodyDist X - 20) / 5.0, 0))

[State 751, Golpe 1]
type = HitDef
trigger1 = Anim = 210
trigger1 = AnimElemTime(1) = 0
trigger1 = EnemyNear, MoveType != H
trigger2 = Anim = 210
trigger2 = AnimElemTime(1) = 0
trigger2 = EnemyNear, GetHitVar(hitcount) < 16
attr = S, NA
damage = 22, 0
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
sparkxy = -10, -145
ground.hittime = 22
air.hittime = 22
ground.velocity = 0
air.velocity = 0, -5

[State 751, Golpe 1 (pasó del límite)]
type = HitDef
trigger1 = Anim = 210
trigger1 = AnimElemTime(1) = 0
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 16
attr = S, NA
damage = 22, 0
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
sparkxy = -10, -145
ground.hittime = 22
air.hittime = 22
ground.velocity = -12, -10
air.velocity = -12, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 751, Golpe 2: animación]
type = ChangeAnim
trigger1 = Anim = 210
trigger1 = AnimTime = 0
value = 240

[State 751, Acercarse 2]
type = VelSet
trigger1 = Anim = 240
trigger1 = AnimElemTime(1) = 0
x = ifelse(P2BodyDist X > 60, 16, ifelse(P2BodyDist X > 20, (P2BodyDist X - 20) / 5.0, 0))

[State 751, Golpe 2 (último autodoble del combo)]
type = HitDef
trigger1 = Anim = 240
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) >= 4
attr = S, NA
damage = 22, 0
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
sparkxy = -10, -96
ground.hittime = 46
air.hittime = 46
ground.velocity = -7.2, -12
air.velocity = -7.2, -12
fall = 1
air.fall = 1
fall.recover = 0

[State 751, Golpe 2]
type = HitDef
trigger1 = Anim = 240
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) < 4
trigger1 = EnemyNear, MoveType != H
trigger2 = Anim = 240
trigger2 = AnimElemTime(1) = 0
trigger2 = Time > 0
trigger2 = Map(sm_adn) < 4
trigger2 = EnemyNear, GetHitVar(hitcount) < 16
attr = S, NA
damage = 22, 0
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
sparkxy = -10, -96
ground.hittime = 46
air.hittime = 46
ground.velocity = 0
air.velocity = 0, -5

[State 751, Golpe 2 (pasó del límite)]
type = HitDef
trigger1 = Anim = 240
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) < 4
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 16
attr = S, NA
damage = 22, 0
animtype = Medium
guardflag = MA
hitflag = MAF
priority = 4, Hit
pausetime = 11, 11
sparkno = 1
guard.sparkno = 40
hitsound = 5, 1
guardsound = 6, 0
ground.type = High
ground.slidetime = 11
sparkxy = -10, -96
ground.hittime = 46
air.hittime = 46
ground.velocity = -12, -10
air.velocity = -12, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 751, Fin]
type = ChangeState
trigger1 = Anim = 240
trigger1 = AnimTime = 0
trigger1 = Time > 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Autodoble (Fuerte)
[Statedef 752]
type = S
movetype = A
physics = S
juggle = 0
velset = 0, 0
ctrl = 0
anim = 220
poweradd = 15
sprpriority = 2

[State 752, Cuenta de autodobles]
type = MapAdd
trigger1 = Time = 0
map = "sm_adn"
value = 1

[State 752, Correr hasta el rival]
type = ChangeAnim
trigger1 = Time = 0
trigger1 = P2BodyDist X > 60
value = 100

[State 752, Correr hasta el rival (2)]
type = VelSet
trigger1 = Anim = 100
x = 16

[State 752, Llegó]
type = ChangeAnim
trigger1 = Anim = 100
trigger1 = P2BodyDist X <= 30 || Time >= 45
value = 220

[State 752, Llegó (2)]
type = VelSet
trigger1 = Anim = 220
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
x = 0

[State 752, Acercarse]
type = VelSet
trigger1 = Time = 0
x = ifelse(P2BodyDist X > 60, 16, ifelse(P2BodyDist X > 20, (P2BodyDist X - 20) / 5.0, 0))

[State 752, Golpe 1]
type = HitDef
trigger1 = Anim = 220
trigger1 = AnimElemTime(1) = 0
trigger1 = EnemyNear, MoveType != H
trigger2 = Anim = 220
trigger2 = AnimElemTime(1) = 0
trigger2 = EnemyNear, GetHitVar(hitcount) < 16
attr = S, NA
damage = 30, 0
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
sparkxy = -10, -146
ground.hittime = 26
air.hittime = 26
ground.velocity = 0
air.velocity = 0, -5

[State 752, Golpe 1 (pasó del límite)]
type = HitDef
trigger1 = Anim = 220
trigger1 = AnimElemTime(1) = 0
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 16
attr = S, NA
damage = 30, 0
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
sparkxy = -10, -146
ground.hittime = 26
air.hittime = 26
ground.velocity = -12, -10
air.velocity = -12, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 752, Golpe 2: animación]
type = ChangeAnim
trigger1 = Anim = 220
trigger1 = AnimTime = 0
value = 250

[State 752, Acercarse 2]
type = VelSet
trigger1 = Anim = 250
trigger1 = AnimElemTime(1) = 0
x = ifelse(P2BodyDist X > 60, 16, ifelse(P2BodyDist X > 20, (P2BodyDist X - 20) / 5.0, 0))

[State 752, Golpe 2 (último autodoble del combo)]
type = HitDef
trigger1 = Anim = 250
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) >= 4
attr = S, NA
damage = 30, 0
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
sparkxy = -10, -153
ground.hittime = 54
air.hittime = 54
ground.velocity = -7.2, -12
air.velocity = -7.2, -12
fall = 1
air.fall = 1
fall.recover = 0

[State 752, Golpe 2]
type = HitDef
trigger1 = Anim = 250
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) < 4
trigger1 = EnemyNear, MoveType != H
trigger2 = Anim = 250
trigger2 = AnimElemTime(1) = 0
trigger2 = Time > 0
trigger2 = Map(sm_adn) < 4
trigger2 = EnemyNear, GetHitVar(hitcount) < 16
attr = S, NA
damage = 30, 0
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
sparkxy = -10, -153
ground.hittime = 54
air.hittime = 54
ground.velocity = 0
air.velocity = 0, -5

[State 752, Golpe 2 (pasó del límite)]
type = HitDef
trigger1 = Anim = 250
trigger1 = AnimElemTime(1) = 0
trigger1 = Time > 0
trigger1 = Map(sm_adn) < 4
trigger1 = EnemyNear, MoveType = H
trigger1 = EnemyNear, GetHitVar(hitcount) >= 16
attr = S, NA
damage = 30, 0
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 14, 14
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 14
sparkxy = -10, -153
ground.hittime = 54
air.hittime = 54
ground.velocity = -12, -10
air.velocity = -12, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 752, Fin]
type = ChangeState
trigger1 = Anim = 250
trigger1 = AnimTime = 0
trigger1 = Time > 0
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Tatsu-geri (fuerte) (Remate)
[Statedef 4020]
type = S
movetype = A
physics = N
velset = 0, 0
juggle = 4
ctrl = 0
anim = 1200
poweradd = 40
sprpriority = 2

[State 4020, Golpe]
type = HitDef
trigger1 = AnimElem = 2
attr = S, SA
damage = 109, 10
animtype = Heavy
guardflag = MA
hitflag = MAF
priority = 5, Hit
pausetime = 12, 12
sparkno = 2
guard.sparkno = 40
hitsound = 5, 2
guardsound = 6, 0
ground.type = High
ground.slidetime = 12
ground.hittime = 34
air.hittime = 34
sparkxy = -10, -60
ground.velocity = -9, -12
air.velocity = -9, -10
fall = 1
air.fall = 1
fall.recover = 0

[State 4020, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 1
x = 16.25

[State 4020, Moverse / impulso]
type = VelSet
trigger1 = AnimElem = 5
x = 0

[State 4020, Fin]
type = ChangeState
trigger1 = AnimTime = 0
trigger1 = statetype != A
value = 0
ctrl = 1

;---------------------------------------------------------------------------
; Poses al azar: 180, 182
[Statedef 180]
type = S
movetype = I
physics = S
ctrl = 0
velset = 0, 0
anim = 180

[State 180, SM: Pose al azar]
type = ChangeAnim
trigger1 = Time = 0
value = ifelse(Random % 2 = 0, 180, 182)


