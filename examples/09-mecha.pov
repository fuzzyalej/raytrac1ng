// 09-mecha.pov — Iron Sentinel war robot
//
// Advanced scene using all six primitive types:
//   Box      — torso, chest plate, head, hips, feet, pauldrons, vents, fist
//   Cylinder — thighs, upper arms, forearms, neck, cannon barrel, antennas, missiles
//   Sphere   — knees, elbows, shoulder joints, energy core, eyes, cannon pods
//   Torus    — knee rings, shoulder accent rings, cannon muzzle ring
//   Cone     — missile warheads
//   Plane    — metal floor, dark rear wall
//
// Render suggestion:
//   python3 main.py examples/09-mecha.pov -W 800 -H 600 -j 0 --aa 2

camera { location <2, 9, -36>  look_at <0, 7, 0>  fov 42 }

// Key light — upper front right
light { position <18, 28, -12>  radius 2.5  samples 4 }
// Fill light — front left
light { position <-12, 16, -14> }
// Low accent light — illuminates cannon arm and lower body
light { position <-8, 3, -20> }

// ---------------------------------------------------------------------------
// ENVIRONMENT
// ---------------------------------------------------------------------------

// Dark metal battle-ground
plane { normal <0,1,0>  offset 0  color <0.14,0.14,0.17>  reflect 0.20 }
// Rear wall
plane { normal <0,0,-1>  offset -10  color <0.10,0.10,0.12> }

// ---------------------------------------------------------------------------
// FEET
// ---------------------------------------------------------------------------

// Right foot — heel block
box { min <0.3,0.0,-0.6>   max <2.7,1.2,2.0>   color <0.26,0.28,0.35>  reflect 0.40 }
// Right foot — toe block (extends toward camera)
box { min <0.5,0.0,-2.4>   max <2.5,0.8,0.0>   color <0.22,0.24,0.30>  reflect 0.35 }

// Left foot — heel block
box { min <-2.7,0.0,-0.6>  max <-0.3,1.2,2.0>  color <0.26,0.28,0.35>  reflect 0.40 }
// Left foot — toe block
box { min <-2.5,0.0,-2.4>  max <-0.5,0.8,0.0>  color <0.22,0.24,0.30>  reflect 0.35 }

// ---------------------------------------------------------------------------
// LOWER LEGS
// ---------------------------------------------------------------------------

// Right shin — main armor block
box { min <0.7,1.2,-0.9>   max <2.3,5.4,1.1>   color <0.28,0.30,0.38>  reflect 0.42 }
// Right shin — front ridge detail
box { min <0.9,1.8,-1.2>   max <2.1,4.8,-0.8>  color <0.22,0.24,0.30>  reflect 0.38 }

// Left shin — main armor block
box { min <-2.3,1.2,-0.9>  max <-0.7,5.4,1.1>  color <0.28,0.30,0.38>  reflect 0.42 }
// Left shin — front ridge detail
box { min <-2.1,1.8,-1.2>  max <-0.9,4.8,-0.8>  color <0.22,0.24,0.30>  reflect 0.38 }

// ---------------------------------------------------------------------------
// KNEE JOINTS
// ---------------------------------------------------------------------------

// Right knee — ball joint
sphere { center <1.5,5.4,0.1>   radius 0.78  color <0.20,0.22,0.26>  reflect 0.52 }
// Right knee — glowing ring
torus  { center <1.5,5.4,0.1>   axis <0,1,0>  major_radius 0.78  minor_radius 0.20
         color <0.05,0.65,1.0>  reflect 0.35 }

// Left knee — ball joint
sphere { center <-1.5,5.4,0.1>  radius 0.78  color <0.20,0.22,0.26>  reflect 0.52 }
// Left knee — glowing ring
torus  { center <-1.5,5.4,0.1>  axis <0,1,0>  major_radius 0.78  minor_radius 0.20
         color <0.05,0.65,1.0>  reflect 0.35 }

// ---------------------------------------------------------------------------
// THIGHS
// ---------------------------------------------------------------------------

cylinder { bottom <1.2,5.5,0.1>   top <0.9,8.0,0.0>   radius 0.95
           color <0.28,0.30,0.38>  reflect 0.42 }
cylinder { bottom <-1.2,5.5,0.1>  top <-0.9,8.0,0.0>  radius 0.95
           color <0.28,0.30,0.38>  reflect 0.42 }

// ---------------------------------------------------------------------------
// HIPS / PELVIS
// ---------------------------------------------------------------------------

// Main pelvis block
box { min <-2.6,7.2,-1.3>  max <2.6,8.8,1.3>  color <0.26,0.28,0.35>  reflect 0.40 }
// Right hip side armor
box { min <2.5,7.4,-0.9>   max <3.5,8.5,0.9>  color <0.20,0.22,0.26>  reflect 0.35 }
// Left hip side armor
box { min <-3.5,7.4,-0.9>  max <-2.5,8.5,0.9>  color <0.20,0.22,0.26>  reflect 0.35 }

// ---------------------------------------------------------------------------
// TORSO / CHEST
// ---------------------------------------------------------------------------

// Main chest block
box { min <-3.6,8.4,-1.5>  max <3.6,12.4,1.5>  color <0.28,0.30,0.38>  reflect 0.45 }
// Center chest plate (protrudes forward)
box { min <-1.4,9.0,-1.9>  max <1.4,11.5,-1.4>  color <0.22,0.24,0.30>  reflect 0.50 }
// Plasma energy core — translucent, glowing
sphere { center <0,10.2,-2.1>  radius 0.95  color <0.0,0.82,1.0>
         opacity 0.45  reflect 0.60  ior 1.3 }
// Left chest vent panel
box { min <-3.4,9.2,-1.6>  max <-1.7,11.0,-1.4>  color <0.12,0.13,0.16> }
// Right chest vent panel
box { min <1.7,9.2,-1.6>   max <3.4,11.0,-1.4>   color <0.12,0.13,0.16> }

// ---------------------------------------------------------------------------
// NECK
// ---------------------------------------------------------------------------

cylinder { bottom <0,12.2,0>  top <0,13.0,0>  radius 0.65
           color <0.20,0.22,0.26>  reflect 0.48 }

// ---------------------------------------------------------------------------
// HEAD
// ---------------------------------------------------------------------------

// Main head block
box { min <-1.6,12.8,-1.3>  max <1.6,15.2,1.3>  color <0.28,0.30,0.38>  reflect 0.45 }
// Face plate
box { min <-1.3,13.3,-1.7>  max <1.3,14.8,-1.2>  color <0.20,0.22,0.26>  reflect 0.50 }
// Visor strip (glowing blue)
box { min <-1.4,13.9,-1.8>  max <1.4,14.4,-1.6>  color <0.05,0.75,1.0>  reflect 0.65 }
// Left eye (hot orange)
sphere { center <-0.70,14.1,-1.9>  radius 0.30  color <1.0,0.40,0.02>  reflect 0.55 }
// Right eye
sphere { center <0.70,14.1,-1.9>   radius 0.30  color <1.0,0.40,0.02>  reflect 0.55 }
// Left cheek guard
box { min <-2.0,13.2,-0.8>  max <-1.5,14.9,0.8>  color <0.22,0.24,0.30>  reflect 0.40 }
// Right cheek guard
box { min <1.5,13.2,-0.8>   max <2.0,14.9,0.8>   color <0.22,0.24,0.30>  reflect 0.40 }
// Left antenna
cylinder { bottom <-1.1,15.2,0>  top <-1.5,17.2,0>  radius 0.10
           color <0.18,0.20,0.24>  reflect 0.40 }
// Right antenna
cylinder { bottom <1.1,15.2,0>   top <1.5,17.2,0>   radius 0.10
           color <0.18,0.20,0.24>  reflect 0.40 }

// ---------------------------------------------------------------------------
// SHOULDER PAULDRONS
// ---------------------------------------------------------------------------

// Right pauldron — large armored plate
box { min <3.4,10.2,-2.2>  max <6.4,12.8,2.2>  color <0.28,0.30,0.38>  reflect 0.45 }
// Right shoulder ball joint
sphere { center <3.6,11.0,0>  radius 0.95  color <0.20,0.22,0.26>  reflect 0.52 }
// Right shoulder accent ring
torus  { center <4.9,11.5,0>  axis <1,0,0>  major_radius 0.95  minor_radius 0.24
         color <0.05,0.65,1.0>  reflect 0.38 }

// Left pauldron
box { min <-6.4,10.2,-2.2>  max <-3.4,12.8,2.2>  color <0.28,0.30,0.38>  reflect 0.45 }
// Left shoulder ball joint
sphere { center <-3.6,11.0,0>  radius 0.95  color <0.20,0.22,0.26>  reflect 0.52 }
// Left shoulder accent ring
torus  { center <-4.9,11.5,0>  axis <1,0,0>  major_radius 0.95  minor_radius 0.24
         color <0.05,0.65,1.0>  reflect 0.38 }

// ---------------------------------------------------------------------------
// UPPER ARMS  (angled outward and downward from pauldron)
// ---------------------------------------------------------------------------

cylinder { bottom <4.5,10.4,0>   top <5.4,8.0,0>   radius 0.82
           color <0.26,0.28,0.35>  reflect 0.42 }
cylinder { bottom <-4.5,10.4,0>  top <-5.4,8.0,0>  radius 0.82
           color <0.26,0.28,0.35>  reflect 0.42 }

// ---------------------------------------------------------------------------
// ELBOW JOINTS
// ---------------------------------------------------------------------------

sphere { center <5.4,8.0,0>   radius 0.78  color <0.20,0.22,0.26>  reflect 0.55 }
sphere { center <-5.4,8.0,0>  radius 0.78  color <0.20,0.22,0.26>  reflect 0.55 }

// ---------------------------------------------------------------------------
// FOREARMS
// ---------------------------------------------------------------------------

cylinder { bottom <5.4,7.8,0>   top <5.8,5.2,0>   radius 0.70
           color <0.26,0.28,0.35>  reflect 0.42 }
cylinder { bottom <-5.4,7.8,0>  top <-5.8,5.2,0>  radius 0.70
           color <0.26,0.28,0.35>  reflect 0.42 }

// ---------------------------------------------------------------------------
// RIGHT FIST
// ---------------------------------------------------------------------------

box { min <5.1,3.8,-0.72>  max <6.5,5.2,0.72>  color <0.24,0.26,0.32>  reflect 0.40 }

// ---------------------------------------------------------------------------
// LEFT ARM — PLASMA CANNON (weapon arm, points downward)
// ---------------------------------------------------------------------------

// Cannon housing — large cylinder mounted below forearm
cylinder { bottom <-5.8,5.0,0>  top <-5.8,2.8,0>  radius 0.88
           color <0.12,0.13,0.16>  reflect 0.30 }
// Cannon barrel — narrow, pointing down toward ground
cylinder { bottom <-5.8,2.8,0>  top <-5.8,0.5,0>  radius 0.44
           color <0.08,0.09,0.11>  reflect 0.22 }
// Muzzle ring — glowing cyan
torus  { center <-5.8,0.5,0>  axis <0,1,0>  major_radius 0.52  minor_radius 0.16
         color <0.05,0.65,1.0>  reflect 0.40 }
// Cannon side energy pod — left
sphere { center <-5.0,3.8,-0.9>  radius 0.45  color <0.0,0.82,1.0>  reflect 0.55 }
// Cannon side energy pod — right
sphere { center <-6.6,3.8,-0.9>  radius 0.45  color <0.0,0.82,1.0>  reflect 0.55 }

// ---------------------------------------------------------------------------
// MISSILE LAUNCHER (mounted on right shoulder top, missiles point forward)
// ---------------------------------------------------------------------------

// Launcher housing block
box { min <3.8,12.7,-1.5>  max <6.2,13.8,1.5>  color <0.16,0.17,0.20>  reflect 0.30 }
// Left missile tube (cylinder axis in -Z, toward camera)
cylinder { bottom <4.5,13.2,-1.5>  top <4.5,13.2,-4.5>  radius 0.28
           color <0.12,0.13,0.16>  reflect 0.25 }
// Right missile tube
cylinder { bottom <5.5,13.2,-1.5>  top <5.5,13.2,-4.5>  radius 0.28
           color <0.12,0.13,0.16>  reflect 0.25 }
// Left warhead — cone tapering to a point
cone { bottom <4.5,13.2,-4.5>  top <4.5,13.2,-5.8>
       bottom_radius 0.28  top_radius 0.0
       color <0.85,0.18,0.08>  reflect 0.25 }
// Right warhead
cone { bottom <5.5,13.2,-4.5>  top <5.5,13.2,-5.8>
       bottom_radius 0.28  top_radius 0.0
       color <0.85,0.18,0.08>  reflect 0.25 }
