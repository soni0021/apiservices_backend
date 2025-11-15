from pydantic import BaseModel
from typing import Optional, List


class VoterIDSplitAddress(BaseModel):
    district: Optional[List[str]] = None
    state: Optional[List[List[str]]] = None
    city: Optional[List[str]] = None
    pincode: Optional[str] = None
    country: Optional[List[str]] = None
    address_line: Optional[str] = None


class VoterIDData(BaseModel):
    epic_number: str
    status: Optional[str] = None
    name: Optional[str] = None
    name_in_regional_lang: Optional[str] = None
    age: Optional[str] = None
    relation_type: Optional[str] = None
    relation_name: Optional[str] = None
    relation_name_in_regional_lang: Optional[str] = None
    father_name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    assembly_constituency_number: Optional[str] = None
    assembly_constituency: Optional[str] = None
    parliamentary_constituency_number: Optional[str] = None
    parliamentary_constituency: Optional[str] = None
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    serial_number: Optional[str] = None
    polling_station: Optional[str] = None
    address: Optional[str] = None
    photo: Optional[str] = None
    split_address: Optional[VoterIDSplitAddress] = None
    urn: Optional[str] = None


class VoterIDResponse(BaseModel):
    status: int
    message: str
    data: Optional[VoterIDData] = None

