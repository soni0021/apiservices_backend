from pydantic import BaseModel
from typing import List


class ChallanRequest(BaseModel):
    vehicle_no: str


class ChallanOffence(BaseModel):
    offenceName: str
    mva: str
    penalty: int


class ChallanRecord(BaseModel):
    regNo: str
    violatorName: str
    dlRcNo: str
    challanNo: str
    challanDate: str
    challanAmount: int
    challanStatus: str
    challanPaymentDate: str
    transactionId: str
    paymentSource: str
    challanUrl: str
    receiptUrl: str
    paymentUrl: str
    state: str
    date: str
    dptCd: int
    rtoCd: int
    courtName: str
    courtAddress: str
    sentToCourtOn: str
    designation: str
    trafficPolice: int
    vehicleImpound: str
    virtualCourtStatus: int
    courtStatus: int
    validContactNo: int
    officeName: str
    areaName: str
    officeText: str
    paymentEligible: int
    statusTxt: str
    paymentGateway: int
    statusDesc: str
    physicalChallan: int
    challanOffences: List[ChallanOffence]


class ChallanCategory(BaseModel):
    count: int
    data: List[ChallanRecord]


class ChallanDataResponse(BaseModel):
    paidChallans: ChallanCategory
    pendingChallans: ChallanCategory
    physicalCourtChallans: ChallanCategory
    virtualCourtChallans: ChallanCategory


class ChallanResponse(BaseModel):
    success: bool
    status: int
    data: ChallanDataResponse
    responseType: int
    message: str
    dataType: int

