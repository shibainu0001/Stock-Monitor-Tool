FUND_ID="03311187"
IMAGE_DIR="/data/data/com.termux/files/home/storage/documents/stock/plot_images"
python update.py $FUND_ID > /dev/null
# python bandwalk.py $FUND_ID $IMAGE_DIR "S&P500"
python bandwalk_core_impl.py $FUND_ID DUMMY_DIR "S&P500"