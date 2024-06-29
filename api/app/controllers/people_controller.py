from fastapi import APIRouter, Depends, HTTPException
from typing import List
from bson import ObjectId

from schemas import Person, PersonCreate
from services.people_service import PeopleService, get_people_service, AlreadyExistsException


people_router = APIRouter(prefix='/people')


@people_router.get('/{person_id}', response_model=Person)
async def read(
        person_id: str,
        people_service: PeopleService = Depends(get_people_service)
):
    try:
        object_id = ObjectId(person_id)  # Convert string to ObjectId
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    person = await people_service.read(object_id)
    if person is None:
        raise HTTPException(status_code=404, detail=f'Person with id={person_id} not found')
    return person


@people_router.get('/', response_model=List[Person])
async def search(
        name: str,
        people_service: PeopleService = Depends(get_people_service)
):
    people = await people_service.search(name)
    return people


@people_router.patch('/{person_id}', response_model=Person)
async def update(
        person_id: str,
        update_data: PersonCreate,
        people_service: PeopleService = Depends(get_people_service)
):
    try:
        object_id = ObjectId(person_id)  # Convert string to ObjectId
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    try:
        updated_url = await people_service.update(object_id, update_data)
    except (AlreadyExistsException) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if updated_url is None:
        raise HTTPException(status_code=404, detail=f'Person with id={person_id} not found')
    return updated_url


@people_router.post('/', response_model=Person)
async def create(
        create_data: PersonCreate,
        people_service: PeopleService = Depends(get_people_service)
):
    try:
        url = await people_service.create(create_data)
    except (AlreadyExistsException) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return url


@people_router.delete('/{person_id}')
async def delete(
        person_id: str,
        people_service: PeopleService = Depends(get_people_service)
):
    try:
        object_id = ObjectId(person_id)  # Convert string to ObjectId
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

    is_deleted = await people_service.delete(object_id)
    if not is_deleted:
        raise HTTPException(status_code=404, detail=f'Url with id={person_id} not found')
