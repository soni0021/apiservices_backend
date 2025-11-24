# Services Status and Database Tables Mapping

## ✅ Services That Work (Have Fallback Engine)

These services use `fallback_engine` which checks DB first, then calls external APIs:

1. **Vehicle RC Verification** (`vehicle-rc-verification`)
   - Table: `rc_data`
   - Method: `fallback_engine.fetch_rc_data()`
   - Status: ✅ Works (has fallback to external APIs)

2. **Driving License API** (`driving-licence`)
   - Table: `licence_data`
   - Method: `fallback_engine.fetch_licence_data()`
   - Status: ✅ Works (has fallback to external APIs)

3. **Challan Detail API** (`challan-detail`)
   - Table: `challan_data`
   - Method: `fallback_engine.fetch_challan_data()`
   - Status: ✅ Works (has fallback to external APIs)

4. **RC to Engine and Chassis Number** (`rc-to-engine-chassis`)
   - Table: `rc_data` (uses RC data via fallback_engine)
   - Status: ✅ Works (uses RC fallback)

5. **Basic Vehicle Info** (`basic-vehicle-info`)
   - Table: `rc_data` (uses RC data via fallback_engine)
   - Status: ✅ Works (uses RC fallback)

## 🔧 Services Fixed (Now Have Fallback Logic)

These services now try external APIs if data not found in DB:

6. **RC to Mobile Number** (`rc-to-mobile`)
   - Table: `rc_mobile_data` (primary), `rc_data` (fallback)
   - Method: Checks `rc_mobile_data`, then tries `rc_data` for mobile number
   - Status: ✅ Fixed (has fallback to RC data)

7. **PAN Verification** (`pan-verification`)
   - Table: `pan_data`
   - Method: Checks DB, then tries external API fallback
   - Status: ✅ Fixed (has external API fallback)

8. **Aadhaar to PAN** (`aadhaar-to-pan`)
   - Table: `pan_data`
   - Method: Checks DB, then tries external API fallback
   - Status: ✅ Fixed (has external API fallback)

9. **PAN to Aadhaar Verification** (`pan-to-aadhaar`)
   - Table: `pan_data`
   - Method: Checks DB, then tries external API fallback
   - Status: ✅ Fixed (has external API fallback)

10. **Address Verification** (`address-verification`)
    - Table: `address_verification_data`
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

11. **GST Verification (Advance)** (`gst-verification`)
    - Table: `gst_data`
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

12. **GST Basic Details** (`gst-basic-details`)
    - Table: `gst_data` (same as GST Verification)
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

13. **GST Address** (`gst-address`)
    - Table: `gst_data` (same as GST Verification)
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

14. **GST Aadhaar Status** (`gst-aadhaar-status`)
    - Table: `gst_data` (same as GST Verification)
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

15. **MSME Verification** (`msme-verification`)
    - Table: `msme_data`
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

16. **Udyam API** (`phone-to-udyam`)
    - Table: `udyam_data`
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

17. **Voter ID Verification** (`voter-id-verification`)
    - Table: `voter_id_data`
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

18. **Fuel Price by City** (`fuel-price-city`)
    - Table: `fuel_price_data`
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

19. **Fuel Price by State** (`fuel-price-state`)
    - Table: `fuel_price_data`
    - Method: Checks DB, then tries external API fallback
    - Status: ✅ Fixed (has external API fallback)

20. **DL to Challan API** (`dl-to-challan`)
    - Table: `dl_challan_data`
    - Method: Checks DB first
    - Status: ⚠️ Needs external API integration (currently only checks DB)

## Database Tables

All services map to these database tables:
- `rc_data` - Vehicle RC information
- `rc_mobile_data` - RC to Mobile mapping
- `licence_data` - Driving License information
- `challan_data` - Vehicle challan/violation data
- `dl_challan_data` - DL to Challan mapping
- `pan_data` - PAN card information
- `address_verification_data` - Aadhaar address verification
- `gst_data` - GST verification data
- `msme_data` - MSME verification data
- `udyam_data` - Udyam registration data
- `voter_id_data` - Voter ID information
- `fuel_price_data` - Fuel price information

## How It Works Now

1. **Service Execution Flow:**
   - Check if API key has access to service (403 if not)
   - Check if service exists and is active (404 if not)
   - Check user credits (402 if insufficient)
   - Execute service logic:
     - Check database for data
     - If not found, try external API fallback (if configured)
     - Return 404 if still not found
   - Deduct credits (only on success)
   - Log usage
   - Return result

2. **External API Fallback:**
   - Services now try external APIs if data not in DB
   - Requires `EXTERNAL_API_1_URL`, `EXTERNAL_API_2_URL`, `EXTERNAL_API_3_URL` to be configured
   - Falls back gracefully if external APIs not configured or fail

## Next Steps

1. **Configure External APIs:** Set `EXTERNAL_API_*_URL` and `EXTERNAL_API_*_KEY` in environment variables
2. **Seed Test Data:** Add test data to database tables for development/testing
3. **Monitor Logs:** Check logs to see if external API calls are being made

