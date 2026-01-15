# kafka_subscribe.py
from pigeon import Topic, subscribe

def run_analysis_sometimes():
    topics = [
        Topic(source="CSDF", subject="Crystalline", action="ExperimentStarted"),
        Topic(source="CSDF", subject="Crystalline", action="ExperimentFinished"),
        Topic(source="TDF", subject="Blender", action="MixtureMixed"),
    ]

    print("Subscribed to topics:")
    for t in topics:
        # Topic may stringify nicely in pigeon; otherwise this prints the object repr
        print(" -", t)

    # Subscribe and read messages
    for topic, message in subscribe(topics):
        # In your installed pigeon version, `topic` is a string like:
        # "CSDF_Crystalline_ExperimentStarted"
        print("\n--- NEW MESSAGE ---")
        print("Topic:", topic)
        print("Message:", message)

if __name__ == "__main__":
    run_analysis_sometimes()
