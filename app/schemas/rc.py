from pydantic import BaseModel
from typing import Optional


class RCRequest(BaseModel):
    reg_no: str


class RCDataResponse(BaseModel):
    viStatus: int
    status: str
    regNo: str
    state: str
    rto: str
    regDate: str
    chassisNo: str
    engineNo: str
    vehicleClass: str
    vehicleColor: str
    maker: str
    makerModal: str
    bodyTypeDesc: str
    fuelType: str
    fuelNorms: str
    ownerName: str
    fatherName: str
    permanentAddress: str
    presentAddress: str
    mobileNo: Optional[str] = None
    ownerSrNo: int
    fitnessUpto: str
    taxUpto: str
    insCompany: str
    insUpto: str
    policyNo: str
    pucNo: Optional[str] = None
    pucUpto: Optional[str] = None
    manufacturedMonthYear: str
    unladenWeight: int
    vehicleGrossWeight: int
    noCylinders: int
    cubicCap: int
    noOfSeats: int
    sleeperCap: int
    standCap: int
    wheelBase: int
    nationalPermitUpto: Optional[str] = None
    nationalPermitNo: Optional[str] = None
    nationalPermitIssuedBy: Optional[str] = None
    financerDetails: str
    permitNo: str
    permitIssueDate: str
    permitFrom: str
    permitUpto: str
    permitType: Optional[str] = None
    blacklistStatus: Optional[str] = None
    nocDetails: Optional[str] = None
    statusOn: str
    nonUseStatus: Optional[str] = None
    nonUseFrom: Optional[str] = None
    nonUseTo: Optional[str] = None
    createdAt: str
    updatedAt: str
    vehicleCategory: str
    rtoCode: str
    responseType: int


class RCResponse(BaseModel):
    success: bool
    status: int
    data: RCDataResponse
    message: str
    dataType: int

