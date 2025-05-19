This is the project for CMAC CSDF 

This code is for station 2



reset tray POS 

http POST http://localhost:8002/reset_tray reset_to=0

manually add task

http POST http://localhost:8000/add_task task:='[1, 5, "A"]'

monitor queue

http GET http://localhost:8000/queue
