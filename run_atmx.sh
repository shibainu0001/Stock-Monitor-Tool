FUND_ID="04315213"
IMAGE_DIR="/data/data/com.termux/files/home/storage/documents/stock/plot_images"
python update.py $FUND_ID > /dev/null
# python bandwalk.py $FUND_ID $IMAGE_DIR ATMX+
python bandwalk_core_impl.py $FUND_ID DUMMY_DIR ATMX+ 180.7 -4.762 0.897 0.603