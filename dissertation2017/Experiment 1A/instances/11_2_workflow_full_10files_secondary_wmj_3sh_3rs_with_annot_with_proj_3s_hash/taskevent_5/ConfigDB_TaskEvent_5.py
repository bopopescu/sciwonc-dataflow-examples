HOST = "ip-172-31-29-102.us-west-2.compute.internal:27017,ip-172-31-29-103.us-west-2.compute.internal:27017,ip-172-31-29-104.us-west-2.compute.internal:27017,ip-172-31-29-105.us-west-2.compute.internal:27017,ip-172-31-29-101.us-west-2.compute.internal:27017,ip-172-31-29-106.us-west-2.compute.internal:27017,ip-172-31-29-107.us-west-2.compute.internal:27017,ip-172-31-29-108.us-west-2.compute.internal:27017,ip-172-31-29-109.us-west-2.compute.internal:27017"
PORT = ""
USER = ""
PASSWORD = ""
DATABASE = "googleh"
READ_PREFERENCE = "secondary"
WRITE_CONCERN = "majority"
COLLECTION_INPUT = "task_events"
COLLECTION_OUTPUT = "task_events_info"
PREFIX_COLUMN = "g_"

ATTRIBUTES = ["event type", "CPU request", "memory request"]
SORT = ["_id.filepath", "_id.numline"]
OPERATION_TYPE = "GROUP_BY_COLUMN"
COLUMN = "event type"
VALUE = ["5"]

INPUT_FILE = "task_events.dat"
OUTPUT_FILE = "task_events_info_5.dat"
