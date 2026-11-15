# csdf_kafka.py

from pigeon import MessageLevel, publish
import datetime

def _now():
    return datetime.datetime.now().isoformat()

responsible_person = "CSDF Gang of Five"
location = "TIC 617"


def device_warning(subject: str, action: str):
    try:
        publish(
            level=MessageLevel.WARNING,
            source="CSDF",
            subject=subject,
            action=action,
            responsible_person=responsible_person,
            maintainer="Sahil Salekar",
            safety_flags="none",
            location=location,
            cmac_id=[],
            datetime=_now(),
        )

    except Exception as e:
        print(f"Error in device warning kafka publish: {e}")


def device_error(subject: str, action: str, safety_flags: str, error_desc: str):
    try:
        publish(
            level=MessageLevel.ERROR,
            source="CSDF",
            subject=subject,
            action=action,
            responsible_person=responsible_person,
            maintainer="Sahil Salekar",
            safety_flags=safety_flags,
            location=location,
            cmac_id=[],
            datetime=_now(),
            error_desc = error_desc,
        )

    except Exception as e:
        print(f"Error in device error kafka publish: {e}")

def station_warning(subject: str, action: str):
    try:
        publish(
            level=MessageLevel.WARNING,
            source="CSDF",
            subject=subject,
            action=action,
            responsible_person=responsible_person,
            maintainer="Sahil Salekar",
            safety_flags="none",
            location=location,
            cmac_id=[],
            datetime=_now(),
        )

    except Exception as e:
        print(f"Error in device warning kafka publish: {e}")

def station_error(action: str, station_no: str, safety_flags: str, error_desc: str):
    try:
        publish(
            level=MessageLevel.ERROR,
            source="CSDF",
            subject="Station_Error",
            action=action,
            responsible_person=responsible_person,
            maintainer="Sahil Salekar",
            safety_flags=safety_flags,
            location=location,
            cmac_id=[],
            datetime=_now(),
            station=f"Station{station_no}",
            error_desc = error_desc,
        )

    except Exception as e:
        print(f"Error in station error kafka publish: {e}")



