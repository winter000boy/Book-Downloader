import re
import hashlib
import requests
import argparse
from bs4 import BeautifulSoup

keySalt = "aB1cD2eF3G"
customer_id = '5157796'

# Parse Arguments
parser = argparse.ArgumentParser(description='Download KKBooks')
parser.add_argument('-u', '--url', help='URL of Book on KopyKitab')

args = parser.parse_args()

if args.url is None:
    parser.print_help()
    exit(0)

# Ref: https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
# URL Sanitization
urlRegex = re.compile(
    r'^(?:http|ftp)s?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

# URL Check
if re.match(urlRegex, args.url) is None:
    print("Please Provide Valid URL")
    exit(0)

print('[=>] KKBook Downloader Starting')
print('[=>] Getting Book Details')
product = requests.get(args.url)

if product.status_code != 200:
    print("[X] Book Not Found!")
    exit(0)

print('[=>] Found Book Details')

try:
    productData = BeautifulSoup(product.text, 'html5lib')
except:
    print("[!] html5lib parser not found, falling back to html.parser")
    productData = BeautifulSoup(product.text, 'html.parser')

print('[=>] Parsing Book Details')
product_id = str(productData.find("input", attrs={"name": "product_id"})['value'])

print('[=>] Found Book ID:', product_id)
print('[=>] Getting Book Data from Library')
bookLibrary = requests.post('https://www.kopykitab.com/index.php?route=account/profileelib/app_library',
                            data={'customer_id': customer_id})

if bookLibrary.status_code != 200:
    print("[X] Books Data Fetching Failed!")
    exit(0)

# Get Book Details
booklib = bookLibrary.json()

if not booklib['status']:
    print("[X] Books Data Result Failed!")
    exit(0)

print('[=>] Checking If Book Available in Library')

needToAdd = True
product_link = None

# Check Book Entry in Library
bookList = booklib['results'][0]['products'][0]['products']
for book in bookList:
    if product_id in book['product_id']:
        needToAdd = False
        product_link = book['product_link']
        print("[=>] Found Book in Library")

# Query to Book Library
if needToAdd:
    print("[=>] Not Found, Adding Book into Library")
    addToLib = requests.get('https://www.kopykitab.com/index.php', params={
        'route': 'account/applogin/createOrderByProductId',
        'product_ids': product_id,
        'customer_id': customer_id
    })

    if addToLib.status_code != 200:
        print("[X] Failed to Add Book in Library!")
        exit(0)

    print('[=>] Getting New Book Data from Library')
    bookLibrary = requests.post('https://www.kopykitab.com/index.php?route=account/profileelib/app_library',
                                data={'customer_id': customer_id})

    if bookLibrary.status_code != 200:
        print("[X] Books Data Fetching Failed!")
        exit(0)

    booklib = bookLibrary.json()

    if not booklib['status']:
        print("[X] New Books Data Result Failed!")
        exit(0)

    bookList = booklib['results'][0]['products'][0]['products']
    for book in bookList:
        if product_id in book['product_id']:
            needToAdd = False
            product_link = book['product_link']
            print("[=>] Found New Book in Library")

# Calculate Password for PDF
pdfPass = hashlib.md5((keySalt + product_id).encode()).hexdigest()
filePath = args.url.split('.com/')[1] + '-' + str(pdfPass) + ".pdf"

print("[=>] PDF Password:", pdfPass)

# Download PDF from Link
with open(filePath, "wb") as f:
    print("[=>] Downloading %s " % filePath, sep='')
    response = requests.get(product_link, allow_redirects=True, stream=True)

    if response.status_code == 200:
        total_length = response.headers.get('content-length')

        if total_length is None:  # no content length header
            f.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                done = int(50 * dl / total_length)
                # Progress Bar
                print("\r[%s%s]" % ('=' * done, ' ' * (50 - done)), sep='', end='\r', flush=True)
        print("\n[=>] File Downloaded", flush=True)
    else:
        print("[X] Failed to Download File!", flush=True)
        exit(0)

print("[=>] KKBook Downloader Process Complete")
