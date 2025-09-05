FUND_ID="04315213"
IMAGE_DIR="/data/data/com.termux/files/home/storage/documents/stock/plot_images"
python update.py $FUND_ID > /dev/null
# python bandwalk.py $FUND_ID $IMAGE_DIR ATMX+

UPPER_THRESHOLD=180.94
UPPER_CROSS_RATE=0.82
LOWER_THRESHOLD=-4.65
LOWER_CROSS_RATE=0.619

python bandwalk_core_impl.py $FUND_ID DUMMY_DIR ATMX+ $UPPER_THRESHOLD $LOWER_THRESHOLD $UPPER_CROSS_RATE $LOWER_CROSS_RATE