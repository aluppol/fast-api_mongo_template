from datetime import datetime
from pymongo import ReturnDocument
from typing import List
import aiohttp
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from fastapi import Depends
from bson import ObjectId

from services.database import get_database_service
from services.http_service import HTTPService, get_http_service
from schemas import PersonCreate, Person
from helpers import get_env_variable


DB_PEOPLE_COLLECTION_NAME = get_env_variable("DB_PEOPLE_COLLECTION_NAME", "People")     # Set if needs be


class AlreadyExistsException(Exception):
    def __init__(self, name: str):
        super().__init__(f"{name} already exists.")


class UrlIsNotValidException(Exception):
    def __init__(self, url: str, description: str):
        super().__init__(f"URL {url} cannot be followed: {description}")


class PeopleService:
    def __init__(self,
                 db: AsyncIOMotorDatabase,
                 https: HTTPService):
        self.collection: AsyncIOMotorCollection[Person] = db.get_collection(DB_PEOPLE_COLLECTION_NAME)
        self.https = https


    async def validate_url(self, url: str):
        """
        Validates a URL by sending an HTTP GET request.

        Args:
            url (str): The URL to validate.

        Raises:
            UrlNotValidException: If the URL is not valid (response status is 400 or higher)
                or there is a client-side error.
        """
        try:
            response = await self.https.fetch_url(url)
            if response.status >= 400:
                raise UrlIsNotValidException(url, response.reason)
        except aiohttp.ClientError as e:
            raise UrlIsNotValidException(url, str(e))


    async def create(self, person_payload: PersonCreate) -> Person:
        """
        Raises:
            PersonAlreadyExistsException: If the person's name already exists in the database.
        """
    
        person_from_db = await self.collection.find_one({ 'name': person_payload.name, "$or": [
                {"deleted_at": {"$exists": False}},
                {"deleted_at": None}
            ] })
        if person_from_db:
            raise AlreadyExistsException(person_from_db)

        person = {
            **person_payload.model_dump(exclude_unset=True),
            "created_at": datetime.now(),
        }

        result = await self.collection.insert_one(person)
        person['_id'] = result.inserted_id
        return Person(**person)


    async def read(self, person_id: ObjectId=None, include_deleted=False, name=None) -> Person:
        query = {}
        if person_id is not None:
            query['_id'] = person_id

        if name is not None:
            query['name'] = name

        if not include_deleted:
            query["$or"] = [
                {"deleted_at": {"$exists": False}},
                {"deleted_at": None}
            ]

        result = await self.collection.find_one(query)
        return Person(**result) if result else None

    async def search(self, name: str, include_deleted: bool=False, page: int=1, page_size: int=10) -> List[Person]:
        query = {
            'name': {'$regex': f'.*{name}.*', '$options': 'i' },
        }

        if not include_deleted:
            query["$or"] = [
                {"deleted_at": {"$exists": False}},
                {"deleted_at": None}
            ]

        skip = (page - 1) * page_size

        result = []

        async for person in self.collection.find(query).skip(skip).limit(page_size):
            result.append(Person(**person))

        return result


    async def update(self, person_id: ObjectId,  person_payload: PersonCreate, include_deleted=False) -> Person:
        """
        Raises:
            PersonAlreadyExistsException: If the Person already exists in the database with the given name.
        """
        validation_query = { 'name': person_payload.name, 'deleted_at': None }
        if not include_deleted:
            validation_query["$or"] = [
                {"deleted_at": {"$exists": False}},
                {"deleted_at": None}
            ]
        
        person_from_db = await self.collection.find_one(validation_query)
        if person_from_db:
            raise AlreadyExistsException(person_from_db)

        update_data = {
            **person_payload.model_dump(exclude_unset=True),
            "updated_at": datetime.now(),
        }


        query = {"_id": person_id}
        if not include_deleted:
            query["$or"] = [
                {"deleted_at": {"$exists": False}},
                {"deleted_at": None}
            ]
        result = await self.collection.find_one_and_update(
            query,
            {"$set": update_data},
            return_document=ReturnDocument.AFTER,
        )

        return Person(**result) if result else None


    async def delete(self, person_id: ObjectId) -> bool:
        result = await self.collection.update_one(
            {'_id': person_id, '$or': [
                {"deleted_at": {"$exists": False}},
                {"deleted_at": None}
            ] },
            {"$set": {"deleted_at": datetime.now()}}
        )

        return result.modified_count > 0


async def get_people_service(
        dbs=Depends(get_database_service),
        https=Depends(get_http_service),
):
    return PeopleService(dbs.get_database(), https)
