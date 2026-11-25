from datetime import date
from fastapi import APIRouter, Request

router = APIRouter(prefix='/api', tags=['schedule'])


@router.get('/doctors')
async def doctors(request: Request):
    return await request.app.state.appointments.doctors()


@router.get('/slots')
async def slots(request: Request, doctor_id: int | None = None, day: date | None = None):
    return await request.app.state.appointments.availability(doctor_id, day)


@router.get('/appointments')
async def appointments(request: Request):
    return await request.app.state.appointments.dashboard_appointments()
