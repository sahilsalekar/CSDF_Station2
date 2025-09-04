# kafka.py

from pigeon import MessageLevel, publish
import datetime

dt = datetime.datetime.now()
responsible_person = "Sahil Salekar"
location = "TIC 617"

def experiment_started(exp_id: int, crystalline_id: int, reactor_id: str):
    publish(
        level=MessageLevel.INFO,
        source="CSDF",
        subject="Crystalline",
        action="ExperimentStarted",
        responsible_person=responsible_person,
        safety_flags="none",
        location=location,
        exp_id=exp_id, 
        crystalline_id=crystalline_id,
        reactor_id=reactor_id,
        datetime=dt
    )

def experiment_finished(exp_id: int, crystalline_id: int, reactor_id: str):
    publish(
        level=MessageLevel.INFO,
        source="CSDF",
        subject="Crystalline",
        action="ExperimentFinished",
        responsible_person=responsible_person,
        safety_flags="none",
        location=location,
        exp_id=exp_id, 
        crystalline_id=crystalline_id,
        reactor_id=reactor_id,
        datetime=dt
    )

def experiment_finished(exp_id: int, crystalline_id: int, reactor_id: str):
    publish(
        level=MessageLevel.INFO,
        source="CSDF",
        subject="Crystalline",
        action="ExperimentFinished",
        responsible_person=responsible_person,
        safety_flags="none",
        location=location,
        exp_id=exp_id, 
        crystalline_id=crystalline_id,
        reactor_id=reactor_id,
        datetime=dt
    )

def device_warning(action: str):
    publish(
        level=MessageLevel.WARNING,
        source="CSDF",
        subject="Device",
        action=action,
        responsible_person=responsible_person,
        safety_flags="none",
        location=location,
        datetime=dt
    )

def device_error(action: str):
    publish(
        level=MessageLevel.ERROR,
        source="CSDF",
        subject="Device",
        action=action,
        responsible_person=responsible_person,
        safety_flags="none",
        location=location,
        datetime=dt
    )