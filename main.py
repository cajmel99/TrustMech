from fastapi import FastAPI, HTTPException, Path
from database import get_connection
from datetime import timedelta
from schemas import TimeSlotCreate, AppointmentCreate, UserCreate, UserOut, MechanicRegister, MechanicCreate, MechanicOut, ServiceCreate, ServiceOut
import hashlib

app = FastAPI()

# ---------------------- USER REGISTRATION ----------------------

@app.post("/users/", response_model=UserOut)
def register_user(user: UserCreate):
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %(email)s", {"email": user.email})
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

            cur.execute("""
                INSERT INTO users (name, surname, email, phone, password_hash, role, created_at)
                VALUES (%(name)s, %(surname)s, %(email)s, %(phone)s, %(password_hash)s, %(role)s, NOW())
                RETURNING id, email
            """, {
                "name": user.name,
                "surname": user.surname,
                "email": user.email,
                "phone": user.phone,
                "password_hash": hashed_password,
                "role": user.role
            })

            new_user = cur.fetchone()
            return {"id": new_user[0], "email": new_user[1]}


# ---------------------- MECHANIC REGISTRATION ----------------------

@app.post("/mechanics/register", response_model=MechanicOut)
def register_mechanic_full(data: MechanicRegister):
    hashed_password = hashlib.sha256(data.password.encode()).hexdigest()

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Check if user already exists
            cur.execute("SELECT id FROM users WHERE email = %s", (data.email,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already registered")

            # Insert user with role = 'mechanic'
            cur.execute("""
                INSERT INTO users (name, surname, email, phone, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, %s, 'mechanic', NOW())
                RETURNING id
            """, (
                data.name, data.surname, data.email, data.phone, hashed_password
            ))
            user_id = cur.fetchone()[0]

            # Insert mechanic
            cur.execute("""
                INSERT INTO mechanics (user_id, name, address, city, rating, created_at)
                VALUES (%s, %s, %s, %s, 0.0, NOW())
                RETURNING id, name, address, city, rating
            """, (user_id, data.garage_name, data.address, data.city))
            mech = cur.fetchone()

            return {
                "id": mech[0],
                "name": mech[1],
                "address": mech[2],
                "city": mech[3],
                "rating": mech[4]
            }

# Add mechnic to existing user
@app.post("/mechanics/", response_model=MechanicOut)
def register_mechanic(data: MechanicCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Validate user exists and is a mechanic
            cur.execute("SELECT id FROM users WHERE id = %s AND role = 'mechanic'", (data.user_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=400, detail="User is not a mechanic or does not exist")

            # Insert mechanic profile
            cur.execute("""
                INSERT INTO mechanics (user_id, name, address, city, rating, created_at)
                VALUES (%s, %s, %s, %s, 0.0, NOW())
                RETURNING id, name, city, address, rating
            """, (data.user_id, data.name, data.address, data.city))
            row = cur.fetchone()

            return {
                "id": row[0],
                "name": row[1],
                "city": row[2],
                "address": row[3],
                "rating": row[4]
            }


# ---------------------- MECHANIC BROWSING ----------------------

@app.get("/mechanics/")
def list_mechanics():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, address, city, rating
                FROM mechanics
                ORDER BY rating DESC
            """)
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "address": r[2],
                    "city": r[3],
                    "rating": r[4]
                }
                for r in rows
            ]


@app.get("/mechanics/{mechanic_id}")
def get_mechanic(mechanic_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, name, address, city, rating, created_at
                FROM mechanics
                WHERE id = %s
            """, (mechanic_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Mechanic not found")

            return {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "address": row[3],
                "city": row[4],
                "rating": row[5],
                "created_at": row[6]
            }


# ---------------------- SERVICE MANAGEMENT ----------------------

@app.post("/mechanics/{mechanic_id}/services", response_model=ServiceOut)
def add_service(mechanic_id: int = Path(...), data: ServiceCreate = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM mechanics WHERE id = %s", (mechanic_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Mechanic not found")

            cur.execute("""
                INSERT INTO services (mechanic_id, name, price, duration)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, price, duration
            """, (
                mechanic_id,
                data.name,
                data.price,
                data.duration
            ))

            row = cur.fetchone()
            return {
                "id": row[0],
                "name": row[1],
                "price": row[2],
                "duration": row[3]
            }


@app.get("/mechanics/{mechanic_id}/services")
def list_services(mechanic_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, price, duration
                FROM services
                WHERE mechanic_id = %s
            """, (mechanic_id,))
            rows = cur.fetchall()
            return [
                {"id": r[0], "name": r[1], "price": r[2], "duration": str(r[3])}
                for r in rows
            ]


# ---------------------- TIME SLOTS ----------------------

@app.get("/services/{service_id}/time_slots")
def list_time_slots(service_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, mechanic_id, date, start_time, end_time
                FROM time_slots
                WHERE service_id = %s AND start_time > NOW()
                ORDER BY date, start_time
            """, (service_id,))
            rows = cur.fetchall()
            return [
                {
                    "id": r[0],
                    "mechanic_id": r[1],
                    "date": str(r[2]),
                    "start_time": str(r[3]),
                    "end_time": str(r[4])
                }
                for r in rows
            ]


@app.post("/mechanics/{mechanic_id}/time_slots")
def create_time_slot(mechanic_id: int, slot: TimeSlotCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Confirm mechanic exists
            cur.execute("SELECT id FROM mechanics WHERE id = %s", (mechanic_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Mechanic not found")

            # Validate time block
            if slot.end_time <= slot.start_time:
                raise HTTPException(status_code=400, detail="End time must be after start time")

            # Break into 30-minute slots
            start = slot.start_time
            end = slot.end_time
            delta = timedelta(minutes=30)
            created_slots = []

            while start + delta <= end:
                cur.execute("""
                    INSERT INTO time_slots (mechanic_id, date, start_time, end_time, service_id)
                    VALUES (%s, %s, %s, %s, NULL)
                    RETURNING id
                """, (
                    mechanic_id,
                    slot.date,
                    start,
                    start + delta
                ))
                created_id = cur.fetchone()[0]
                created_slots.append({
                    "id": created_id,
                    "start_time": str(start),
                    "end_time": str(start + delta)
                })
                start += delta

            return {
                "status": "created",
                "slots": created_slots
            }

@app.get("/mechanics/{mechanic_id}/services/{service_id}/available_time_slots")
def get_available_slots_for_service(mechanic_id: int, service_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Get service duration
            cur.execute("""
                SELECT duration FROM services
                WHERE id = %s AND mechanic_id = %s
            """, (service_id, mechanic_id))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Service not found for this mechanic")

            duration_time = result[0]
            service_duration = timedelta(
                hours=duration_time.hour,
                minutes=duration_time.minute,
                seconds=duration_time.second
            )

            # Get all future unbooked slots
            cur.execute("""
                SELECT id, date, start_time, end_time
                FROM time_slots
                WHERE mechanic_id = %s
                  AND appointment_id IS NULL
                  AND start_time > NOW()
                ORDER BY start_time ASC
            """, (mechanic_id,))
            rows = cur.fetchall()

            # Chain slots into available windows
            windows = []
            i = 0
            while i < len(rows):
                slot_chain = []
                total_duration = timedelta()
                start_time = rows[i][2]
                current_end = rows[i][3]

                # Walk forward until enough time accumulated
                for j in range(i, len(rows)):
                    slot_id, date, s_start, s_end = rows[j]
                    if not slot_chain:
                        slot_chain.append(rows[j])
                        total_duration += s_end - s_start
                        current_end = s_end
                    else:
                        if s_start == current_end:
                            slot_chain.append(rows[j])
                            total_duration += s_end - s_start
                            current_end = s_end
                        else:
                            break

                    if total_duration >= service_duration:
                        # Valid window found
                        windows.append({
                            "slot_ids": [s[0] for s in slot_chain],
                            "date": str(date),
                            "start_time": str(start_time),
                            "end_time": str(start_time + service_duration)
                        })
                        break

                i += 1

            return windows


@app.post("/appointments/")
def create_appointment(data: AppointmentCreate):
    from datetime import timedelta

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Get service duration
            cur.execute("""
                SELECT duration FROM services
                WHERE id = %s AND mechanic_id = %s
            """, (data.service_id, data.mechanic_id))
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Service not found for this mechanic")

            duration_time = result[0]
            service_duration = timedelta(
                hours=duration_time.hour,
                minutes=duration_time.minute,
                seconds=duration_time.second
            )

            # Fetch free time slots in order starting from the one selected
            cur.execute("""
                SELECT id, start_time, end_time
                FROM time_slots
                WHERE mechanic_id = %s
                  AND appointment_id IS NULL
                  AND start_time >= (
                    SELECT start_time FROM time_slots WHERE id = %s
                  )
                ORDER BY start_time ASC
            """, (data.mechanic_id, data.time_slot_id))
            slots = cur.fetchall()

            if not slots:
                raise HTTPException(status_code=404, detail="No slots available")

            # Join slots to match duration
            selected_slots = []
            total_duration = timedelta()
            prev_end = None

            for slot in slots:
                slot_id, start, end = slot
                if not selected_slots:
                    selected_slots.append(slot)
                    total_duration += end - start
                    prev_end = end
                elif start == prev_end:
                    selected_slots.append(slot)
                    total_duration += end - start
                    prev_end = end
                else:
                    break  # discontinuity

                if total_duration >= service_duration:
                    break

            if total_duration < service_duration:
                raise HTTPException(status_code=400, detail="Not enough adjacent slots available")

            # Determine exact time needed
            appointment_start = selected_slots[0][1]
            appointment_end = appointment_start + service_duration

            # Insert appointment
            cur.execute("""
                INSERT INTO appointments (
                    client_id, mechanic_id, service_id,
                    date, time, status, start_time, end_time
                )
                VALUES (%s, %s, %s, %s, %s, 'scheduled', %s, %s)
                RETURNING id
            """, (
                data.client_id,
                data.mechanic_id,
                data.service_id,
                appointment_start.date(),
                appointment_start.time(),
                appointment_start,
                appointment_end
            ))
            appointment_id = cur.fetchone()[0]

            # Update slots 
            remaining_duration = service_duration
            for slot in selected_slots:
                slot_id, start, end = slot
                slot_duration = end - start

                if remaining_duration >= slot_duration:
                    # Full slot used
                    cur.execute("""
                        UPDATE time_slots
                        SET appointment_id = %s, service_id = %s
                        WHERE id = %s
                    """, (appointment_id, data.service_id, slot_id))
                    remaining_duration -= slot_duration
                else:
                    # Partial use -> split slot
                    split_point = start + remaining_duration

                    # Update original to booked range
                    cur.execute("""
                        UPDATE time_slots
                        SET end_time = %s, appointment_id = %s, service_id = %s
                        WHERE id = %s
                    """, (split_point, appointment_id, data.service_id, slot_id))

                    # Create remainder as new free slot
                    cur.execute("""
                        INSERT INTO time_slots (mechanic_id, date, start_time, end_time)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        data.mechanic_id,
                        split_point.date(),
                        split_point,
                        end
                    ))

                    break  

            return {
                "appointment_id": appointment_id,
                "status": "confirmed",
                "start_time": str(appointment_start),
                "end_time": str(appointment_end)
            }
