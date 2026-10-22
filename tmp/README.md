# MetroPCS
Availability and estimated shipping dates of cell-phones sold by MetroPCS online.
## Storage
<!-- TABLE_START --><!-- TABLE_END -->
## Tested Environment
✔ Ubuntu 22.04

✔ Windows 11 22H2

✔ macOS 13.5
## Installation
```
git clone https://github.com/dsccccc/MetroPCS.git
cd ./MetroPCS
pip install -r requirements.txt
```

## Price filter
Autoloader and Worker only include promotional prices strictly below $500 USD by default.
For manual runs, change `max_price` in the Run workflow form. Scheduled Autoloader runs use 500.
For local runs, use `python -m script.worker --max_price 300`.
A successful scrape with no matching prices displays a no-matches message; scrape failures preserve the previous README.
