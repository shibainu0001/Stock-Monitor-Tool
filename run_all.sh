FUND_ID="0331418A"
IMAGE_DIR="/data/data/com.termux/files/home/storage/documents/stock/plot_images"
python update.py $FUND_ID > /dev/null
# python bandwalk.py $FUND_ID $IMAGE_DIR "ALL"

UPPER_THRESHOLD=52.99
UPPER_CROSS_RATE=0.952
LOWER_THRESHOLD=-48.92
LOWER_CROSS_RATE=0.999

python bandwalk_core_impl.py $FUND_ID DUMMY_DIR "ALL" $UPPER_THRESHOLD $LOWER_THRESHOLD $UPPER_CROSS_RATE $LOWER_CROSS_RATE