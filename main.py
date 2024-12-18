import krpc
import time
import math

# Подключаемся к серверу kRPC
conn = krpc.connect(name="Mun Satellite Mission")
vessel = conn.space_center.active_vessel

# Потоки телеметрии
altitude = conn.add_stream(getattr, vessel.flight(), 'mean_altitude')
apoapsis = conn.add_stream(getattr, vessel.orbit, 'apoapsis_altitude')
periapsis = conn.add_stream(getattr, vessel.orbit, 'periapsis_altitude')



# 1. Старт ракеты
print("Launching rocket...")
vessel.control.throttle = 1  # Полная тяга
vessel.control.activate_next_stage()  # Включение первой ступени и ускорителей

# Ждем, пока в ускорителях не закончится топливо
print("Monitoring boosters...")
boosters_depleted = False
while not boosters_depleted:
    boosters_depleted = all(
        part.resources.with_resource("SolidFuel")[0].amount <= 0
        for part in vessel.parts.all
        if part.resources.has_resource("SolidFuel")
    )
    time.sleep(0.1)

print("Separating boosters...")
vessel.control.activate_next_stage() # Отделение ускорителей

# Ждем достижения высоты 10 км
while altitude() < 10000:
    time.sleep(0.1)

print("Gravity turn...")
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(75, 90)  # Наклон на 5° от вертикали

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


# Выходим на орбиту (до апоцентра 80 км)
while apoapsis() < 80000:
    time.sleep(0.1)


print("Cutting off engines...")
vessel.control.throttle = 0  # Выключаем двигатели
vessel.auto_pilot.disengage()

while vessel.orbit.time_to_apoapsis > 60:
    time.sleep(1)
vessel.control.activate_next_stage()
vessel.control.activate_next_stage()


# Ждем достижения апоцентра
print("Coasting to apoapsis...")
while vessel.orbit.time_to_apoapsis > 24:
    time.sleep(1)

print("Circularizing orbit...")
vessel.auto_pilot.engage()
vessel.auto_pilot.target_pitch_and_heading(0, 90)
vessel.control.throttle = 1.0  # Включаем двигатели для круговой орбиты

while periapsis() < 70000:
    time.sleep(0.1)

print("Orbit around Kerbin achieved!")
vessel.control.throttle = 0  # Двигатели выключены
time.sleep(2)
vessel.control.activate_next_stage()
vessel.control.activate_next_stage()
vessel.control.activate_next_stage()
time.sleep(2)







# Получаем текущее тело и его орбитальные параметры
kerbin = vessel.orbit.body
mun = conn.space_center.bodies['Mun']

# Гравитационный параметр Кербина
mu = kerbin.gravitational_parameter

# Радиус орбиты Луны
mun_orbit_radius = mun.orbit.semi_major_axis

# Определяем текущую орбиту
current_orbit = vessel.orbit
current_radius = current_orbit.semi_major_axis  # Средний радиус текущей орбиты

# Определяем фазовый угол
vessel_pos = vessel.orbit.body.position(mun.orbital_reference_frame)
mun_pos = mun.position(mun.orbital_reference_frame)
relative_pos = (mun_pos[0] - vessel_pos[0], mun_pos[1] - vessel_pos[1])
phase_angle = math.atan2(relative_pos[1], relative_pos[0])  # В радианах
phase_angle = math.degrees(phase_angle)

print(f"Текущий фазовый угол Луны: {phase_angle:.1f} градусов.")

# Желаемый фазовый угол
desired_phase_angle = 120  # Для выхода на траекторию Луны

# Расчет времени до нужного фазового угла
angle_to_wait = (desired_phase_angle - phase_angle) % 360
wait_time = (angle_to_wait / 360) * current_orbit.period

print(f"Ждать {wait_time:.1f} секунд до маневра.")

# Расчет ∆v для перехода на орбиту Луны
v1 = math.sqrt(mu / current_radius)  # Текущая орбитальная скорость
v2 = math.sqrt(mu * (2 / current_radius - 1 / mun_orbit_radius))  # Скорость выхода на гомановскую траекторию
delta_v = v2 - v1

print(f"∆v для выхода на орбиту Луны: {delta_v:.2f} м/с")

# Создаем маневровый узел
node = vessel.control.add_node(
    conn.space_center.ut + wait_time,
    prograde=delta_v
)

print("Маневр добавлен. Перейдите к узлу и выполните его.")

# Выполнение маневра
ap = conn.space_center.active_vessel.auto_pilot
ap.reference_frame = node.reference_frame
ap.engage()
ap.target_direction = (0, 1, 0)

# Включение двигателей до выполнения маневра
burn_time = node.delta_v / vessel.available_thrust * vessel.mass / vessel.specific_impulse
print(f'Время работы двигателей: {burn_time:.2f} секунд')
conn.space_center.warp_to(node.ut - burn_time / 2)

vessel.control.throttle = 1.0

while node.remaining_delta_v > 1.5:
    remaining_delta_v = node.remaining_delta_v

vessel.control.throttle = 0.0
node.remove()

print("Выход на траекторию Луны завершен!")






# Получение потоков данных
ut = conn.add_stream(getattr, conn.space_center, 'ut')  # Время в игре
body = conn.add_stream(getattr, vessel.orbit, 'body')  # Текущий небесный объект

# Ожидание входа в сферу влияния Муны
print("Ожидание входа в сферу влияния Муны...")
while body() != conn.space_center.bodies['Mun']:
    time.sleep(1)

print("Вход в сферу влияния Муны!")






# Создание маневра для закрепления на орбите Муны
mu = vessel.orbit.body.gravitational_parameter  # Гравитационный параметр Муны
r = vessel.orbit.periapsis  # Радиус в перицентре
v_periapsis = (mu * (2 / r - 1 / vessel.orbit.semi_major_axis)) ** 0.5  # Скорость в перицентре
v_circular = (mu / r) ** 0.5  # Орбитальная скорость для круговой орбиты

dv = v_circular - v_periapsis  # Требуемое изменение скорости для круговой орбиты

node = vessel.control.add_node(
    ut() + vessel.orbit.time_to_periapsis,  # Время маневра (перицентр орбиты)
    prograde=dv  # Ускорение по орбите
)

print(f"Создан маневр: \u0394v = {dv:.2f} м/с")







# Расчет времени выполнения маневра
f = vessel.available_thrust / vessel.mass  # Ускорение корабля
burn_time = abs(dv / f)  # Время выполнения маневра

# Ожидание момента начала маневра
burn_start = ut() + vessel.orbit.time_to_periapsis - burn_time / 2
burn_start = abs(burn_start)
print(f"Время начала маневра: {burn_start}")
while ut() < burn_start:
    time.sleep(0.1)

# Выполнение маневра
ap = conn.space_center.active_vessel.auto_pilot
ap.reference_frame = node.reference_frame
ap.engage()
ap.target_direction = (0, 1, 0)

# Включение двигателей до выполнения маневра
burn_time = node.delta_v / vessel.available_thrust * vessel.mass / vessel.specific_impulse
print(f'Время работы двигателей: {burn_time:.2f} секунд')
conn.space_center.warp_to(node.ut - burn_time / 2)

vessel.control.throttle = 1.0

while node.remaining_delta_v > 1.5:
    remaining_delta_v = node.remaining_delta_v

vessel.control.throttle = 0.0
node.remove()




















# # Константы
# G = 6.67430e-11  # Гравитационная постоянная, м^3/(кг*с^2)
# M_kerbin = 5.2915793e22  # Масса Кербина, кг
# R_kerbin = 600000  # Радиус Кербина, м
# altitude_moon = 12000000  # Высота орбиты Муны, м
#
#
# # Получение текущей орбиты
# orbit = vessel.orbit
# body = orbit.body
#
# # Радиусы орбиты
# r_periapsis = orbit.periapsis  # Радиус в перицентре, м
# r_moon = R_kerbin + altitude_moon  # Радиус орбиты Муны, м
#
# # Полуоси орбит
# semi_major_axis_current = orbit.semi_major_axis  # Полуось текущей орбиты, м
# semi_major_axis_transfer = (r_periapsis + r_moon) / 2  # Полуось переходной орбиты, м
#
# # Функция для расчёта скорости на эллиптической орбите
# def orbital_velocity(semi_major_axis, radius):
#     return math.sqrt(G * M_kerbin * (2 / radius - 1 / semi_major_axis))
#
# # Скорость на текущей орбите в перицентре
# v_periapsis_current = orbital_velocity(semi_major_axis_current, r_periapsis)
#
# # Скорость на переходной орбите в перицентре
# v_periapsis_transfer = orbital_velocity(semi_major_axis_transfer, r_periapsis)
#
# # Дельта-v для выхода на переходную орбиту
# delta_v = v_periapsis_transfer - v_periapsis_current
# print(f"Расчёт завершён: требуемая дельта-v для манёвра {delta_v:.2f} м/с.")
#
# # Создание манёвра
# ut = conn.space_center.ut
# node = vessel.control.add_node(
#     ut + orbit.time_to_periapsis,
#     prograde=delta_v
# )
#
# # Расчёт времени сжигания
# isp = vessel.specific_impulse * 9.81
# thrust = vessel.available_thrust
# mass = vessel.mass
# burn_time = (vessel.mass * delta_v) / thrust
# print(f"Время сжигания: {burn_time:.2f} секунд.")
#
# # Наведение
# ap = vessel.auto_pilot
# ap.reference_frame = node.reference_frame
# ap.target_direction = (0, 1, 0)
# ap.engage()
#
# # Ждем до начала сжигания
# burn_start = node.ut - (burn_time / 2)
# while conn.space_center.ut < burn_start:
#     time.sleep(0.1)
#
# # Сжигание
# vessel.control.throttle = 1.0
# while node.remaining_delta_v > 1.0:
#     time.sleep(0.1)
# vessel.control.throttle = 0
# print("Манёвр завершён!")
# node.remove()















# # Отделение первой ступени
# print("Separating first stage...")
# vessel.control.activate_next_stage()
#
# # 2. Устанавливаем маневр для полета к Луне
# print("Setting transfer to Mun...")
# mun = conn.space_center.bodies['Mun']
# ut = conn.space_center.ut
# node = vessel.control.add_node(
#     ut + vessel.orbit.time_to_apoapsis,  # Маневр у апоцентра
#     prograde=860  # Примерное значение дельта-V для Луны
# )
#
# # Коррекция траектории
# print("Executing transfer maneuver...")
# burn_time = node.delta_v / vessel.available_thrust
# vessel.control.throttle = 1.0
# time.sleep(burn_time)
# vessel.control.throttle = 0
# node.remove()
#
# print("Approaching Mun...")
#
# # Ждем захвата Луной
# while vessel.orbit.body.name != "Mun":
#     time.sleep(1)
#
# print("Captured by Mun gravity. Preparing for orbit...")
# vessel.auto_pilot.engage()
# vessel.auto_pilot.target_pitch_and_heading(0, 90)
# vessel.control.throttle = 1.0
#
# # Торможение для выхода на орбиту Луны
# while periapsis() > 10000:
#     time.sleep(0.1)
#
# vessel.control.throttle = 0
# print("Orbit around Mun achieved!")
#
# # Отделение второй ступени
# print("Separating second stage...")
# vessel.control.activate_next_stage()
#
# # Миссия завершена
# print("Satellite deployed. Mission complete!")
