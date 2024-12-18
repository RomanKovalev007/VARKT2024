import krpc
import time
import math

conn = krpc.connect(name="Mun Satellite Mission")
vessel = conn.space_center.active_vessel

altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude') #высота
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude') #апоцентр
periapsis = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude') #перицентр


print("Запуск!")
vessel.control.throttle = 1
vessel.control.activate_next_stage() #запуск



boosters_depleted = False
while not boosters_depleted:
    boosters_depleted = all(
        part.resources.with_resource("SolidFuel")[0].amount <= 0
        for part in vessel.parts.all
        if part.resources.has_resource("SolidFuel")
    )
    time.sleep(0.1)

print("Отделение ускорителей")
vessel.control.activate_next_stage() #кончается топливо в ускорителях - отсоединение


while altitude() < 10000:
    time.sleep(0.1)

print("Начало наклона...")
vessel.auto_pilot.engage()  #постепенный наклон ракеты
vessel.auto_pilot.target_pitch_and_heading(75, 90)

while altitude() < 15000:
    time.sleep(0.1)
vessel.auto_pilot.target_pitch_and_heading(50, 90)

while altitude() < 20000:
    time.sleep(0.1)
vessel.auto_pilot.target_pitch_and_heading(45, 90)

while altitude() < 30000:
    time.sleep(0.1)
vessel.auto_pilot.target_pitch_and_heading(40, 90)
while altitude() < 40000:
    time.sleep(0.1)
vessel.auto_pilot.target_pitch_and_heading(30, 90)



while apoapsis() < 80000:
    time.sleep(0.1)



vessel.control.throttle = 0  #высота апоазиса - отсключаем двигатели
vessel.auto_pilot.disengage()

while vessel.orbit.time_to_apoapsis > 60:
    time.sleep(1)
vessel.control.activate_next_stage()
vessel.control.activate_next_stage()




while vessel.orbit.time_to_apoapsis > 24:  #оптимальное время для начала выхода на круговую орбиту
    time.sleep(1)

print("Выход на круговую орбиту")
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(0, 90)
vessel.control.throttle = 1.0

while periapsis() < 70000:
    time.sleep(0.1)


print("Вы вышли на орбиту Кербина!")
vessel.control.throttle = 0
time.sleep(2)
vessel.control.activate_next_stage()
vessel.control.activate_next_stage()
vessel.control.activate_next_stage()
time.sleep(2)




kerbin = vessel.orbit.body
mun = conn.space_center.bodies['Mun']


mu = kerbin.gravitational_parameter  #гравитационный параметр


mun_orbit_radius = mun.orbit.semi_major_axis


current_orbit = vessel.orbit #текущая орбита
current_radius = current_orbit.semi_major_axis  #средний радиус текущей орбиты


vessel_pos = vessel.orbit.body.position(mun.orbital_reference_frame)
mun_pos = mun.position(mun.orbital_reference_frame)
relative_pos = (mun_pos[0] - vessel_pos[0], mun_pos[1] - vessel_pos[1])
phase_angle = math.atan2(relative_pos[1], relative_pos[0])
phase_angle = math.degrees(phase_angle)

print(f"Текущий фазовый угол Луны: {phase_angle:.1f} градусов.")


desired_phase_angle = 120


angle_to_wait = (desired_phase_angle - phase_angle) % 360
wait_time = (angle_to_wait / 360) * current_orbit.period #расчет времени до нужного фазового угла

print(f"Ждать {wait_time:.1f} секунд до маневра.")


v1 = math.sqrt(mu / current_radius)  #текущая орбитальная скорость
v2 = math.sqrt(mu * (2 / current_radius - 1 / mun_orbit_radius))  #скорость выхода на гомановскую траекторию
delta_v = v2 - v1

print(f"∆v для выхода на орбиту Луны: {delta_v:.2f} м/с")


node = vessel.control.add_node(
    conn.space_center.ut + wait_time,
    prograde=delta_v
)

print("Маневр добавлен. Перейдите к узлу и выполните его.")


ap = conn.space_center.active_vessel.auto_pilot
ap.reference_frame = node.reference_frame
ap.engage()
ap.target_direction = (0, 1, 0)  #выполнение маневра

# Включение двигателей до выполнения маневра
burn_time = node.delta_v / vessel.available_thrust * vessel.mass / vessel.specific_impulse
print(f'Время работы двигателей: {burn_time:.2f} секунд')
conn.space_center.warp_to(node.ut - burn_time / 2)

vessel.control.throttle = 1.0

while node.remaining_delta_v > 1.5: #погрешность не влияющая на работу
    remaining_delta_v = node.remaining_delta_v

vessel.control.throttle = 0.0
node.remove()

print("Выход на траекторию Луны завершен!")



ut = conn.add_stream(getattr, conn.space_center, 'ut')
body = conn.add_stream(getattr, vessel.orbit, 'body')


print("Ожидание входа в сферу влияния Муны...")
while body() != conn.space_center.bodies['Mun']:
    time.sleep(1)

print("Вход в сферу влияния Муны!")




#создание маневра для закрепления на орбите Муны
mu = vessel.orbit.body.gravitational_parameter  #гравитационный параметр Муны
r = vessel.orbit.periapsis  #радиус в перицентре
v_periapsis = (mu * (2 / r - 1 / vessel.orbit.semi_major_axis)) ** 0.5  #скорость в перицентре
v_circular = (mu / r) ** 0.5  #орбитальная скорость для круговой орбиты

dv = v_circular - v_periapsis

node = vessel.control.add_node(
    ut() + vessel.orbit.time_to_periapsis,
    prograde=dv
)

print(f"Создан маневр: \u0394v = {dv:.2f} м/с")




f = vessel.available_thrust / vessel.mass  #ускорение корабля
burn_time = abs(dv / f)

#ожидаем маневр
burn_start = ut() + vessel.orbit.time_to_periapsis - burn_time / 2
burn_start = abs(burn_start)
print(f"Время начала маневра: {burn_start}")
while ut() < burn_start:
    time.sleep(0.1)


ap = conn.space_center.active_vessel.auto_pilot
ap.reference_frame = node.reference_frame
ap.engage()
ap.target_direction = (0, 1, 0)

#включение двигателей до выполнения маневра
burn_time = node.delta_v / vessel.available_thrust * vessel.mass / vessel.specific_impulse
print(f'Время работы двигателей: {burn_time:.2f} секунд')
conn.space_center.warp_to(node.ut - burn_time / 2)

vessel.control.throttle = 1.0

while node.remaining_delta_v > 1.5:
    remaining_delta_v = node.remaining_delta_v

vessel.control.throttle = 0.0
node.remove()
