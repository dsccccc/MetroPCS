# MetroPCS
Availability and estimated shipping dates of cell-phones sold by MetroPCS online.
## Storage
Price filter: promotional price < $500 USD.

|MetroPCS 10/28/2026|color|memory|eSIM|price|status|shipping from|shipping to|
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
|Apple iPhone 16e|Black|128GB|True|99.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 18 Pro|Burgundy|256GB|True|199.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 18 Pro|Glacier|256GB|True|199.99|NOT_AVAILABLE|11/04/2026|11/09/2026|
|Apple iPhone 18 Pro|Black|256GB|True|199.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 18 Pro|Silver|256GB|True|199.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 18 Pro Max|Burgundy|256GB|True|299.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 18 Pro Max|Silver|256GB|True|299.99|NOT_AVAILABLE|11/04/2026|11/09/2026|
|Apple iPhone 18 Pro Max|Glacier|256GB|True|299.99|NOT_AVAILABLE|11/04/2026|11/09/2026|
|Apple iPhone 18 Pro Max|Black|256GB|True|299.99|NOT_AVAILABLE|11/04/2026|11/09/2026|
|Apple iPhone 17e|White|256GB|True|449.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17e|Black|256GB|True|449.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17e|Soft Pink|256GB|True|449.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17|Lavender|256GB|True|99.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17|Black|256GB|True|99.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17 Pro Max|Cosmic Orange|256GB|True|199.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17 Pro Max|Silver|256GB|True|199.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17 Pro|Cosmic Orange|256GB|True|99.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 17 Pro|Silver|256GB|True|99.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone 15|Black|128GB|True|429.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone Air|Space Black|256GB|True|99.99|AVAILABLE|10/28/2026|11/02/2026|
|Apple iPhone Air|Sky Blue|256GB|True|99.99|AVAILABLE|10/28/2026|11/02/2026|

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
