from pydantic import BaseModel
from typing import List


class LicenceRequest(BaseModel):
    dl_no: str
    dob: str  # Date of birth


class BioObj(BaseModel):
    bioBioId: str
    bioGender: int
    bioGenderDesc: str
    bioBloodGroupname: str
    bioQmQualcd: int
    bioCitiZen: str
    bioUserId: int
    bioFirstName: str
    bioLastName: str
    bioFullName: str
    bioNatName: str
    bioDependentRelation: str
    bioSwdFullName: str
    bioSwdFname: str
    bioPermAdd1: str
    bioPermAdd2: str
    bioPermAdd3: str
    bioTempAdd1: str
    bioTempAdd2: str
    bioTempAdd3: str
    bioDlno: str
    bioPermSdcode: int
    bioTempSdcode: int
    bioRecGenesis: str
    bioEndorsementNo: str
    bioEndorsetime: str
    bioApplno: int
    aadharAuthenticated: bool
    bioDob: str
    bioEndorsedt: str


class BioImgObj(BaseModel):
    biBioId: str
    biusid: int
    biApplno: int
    biPhotoDate: str
    biSignDate: str
    biBioCapturedDt: str
    biConfirmCapture: int
    biPhoto: str
    biSignature: str
    biEndorsedt: int
    biEndorsetime: str
    bdDevId: int


class DLObj(BaseModel):
    dlLicno: str
    bioid: str
    olacode: str
    olaName: str
    statecd: str
    dlApplno: int
    dlUsid: int
    dlIssueauth: str
    dlEndorseno: str
    dlEndorseAuth: str
    dlRecGenesis: str
    dlLatestTrcode: int
    dlStatus: str
    dlRemarks: str
    dlEndorsetime: str
    dlRtoCode: str
    omRtoFullname: str
    omRtoShortname: str
    omOfficeTownname: str
    enforceRemark: str
    dlIntermediateStage: str
    dlIncChallanNo: str
    dlIncSourceType: str
    dlIncRtoAction: str
    dlIssuedt: str
    dlNtValdfrDt: str
    dlNtValdtoDt: str
    dlEndorsedt: str


class DLCoverage(BaseModel):
    dcLicno: str
    dcCovcd: int
    endouserid: int
    olacd: str
    olaName: str
    dcApplno: int
    dcCovStatus: str
    dcEndorseNo: str
    dcEndorsetime: str
    covdesc: str
    covabbrv: str
    vecatg: str
    veShortdesc: str
    dcEndorsedt: str
    dcIssuedt: str


class LicenceResponse(BaseModel):
    errorcd: int
    bioObj: BioObj
    bioImgObj: BioImgObj
    dlobj: DLObj
    dlcovs: List[DLCoverage]
    dbLoc: str

