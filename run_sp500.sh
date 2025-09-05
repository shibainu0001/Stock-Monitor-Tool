FUND_ID="03311187"
IMAGE_DIR="/data/data/com.termux/files/home/storage/documents/stock/plot_images"
python update.py $FUND_ID > /dev/null
# python bandwalk.py $FUND_ID $IMAGE_DIR "S&P500"

UPPER_THRESHOLD=168.6
UPPER_CROSS_RATE=0.970
LOWER_THRESHOLD=-37.4
LOWER_CROSS_RATE=0.856

python bandwalk_core_impl.py $FUND_ID DUMMY_DIR "S&P500" $UPPER_THRESHOLD $LOWER_THRESHOLD $UPPER_CROSS_RATE $LOWER_CROSS_RATE