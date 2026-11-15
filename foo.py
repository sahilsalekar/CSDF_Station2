import csdf_kafka

csdf_kafka.device_error(subject="Balance", action="SI_Unstabel_weight", safety_flags="RestartCode", error_desc="Testing")

#csdf_kafka.station_error(action="robot_error", station_no=2, safety_flags="start code again", error_desc="tcs error")