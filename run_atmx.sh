FUND_ID="04315213"
IMAGE_DIR="/data/data/com.termux/files/home/storage/documents/stock/plot_images"
python update.py $FUND_ID > /dev/null
python bandwalk.py $FUND_ID $IMAGE_DIR