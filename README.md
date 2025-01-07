# MartingaleTrader

## Tutorial
1. Conda environment
```bash
conda create -n martingale_bot python=3.9
conda activate martingale_bot
```
2. Install dependencies based on environment.yml
```bash
conda env update --file environment.yml
```
3. Get your API key from [CoinMarketCap](https://coinmarketcap.com/api/)
4. Create a .env file in the root directory and add the following line
```bash
CMC_API_KEY=your_api_key
```
5. Run the bot in `main.ipynb`, be sure to have the kernel set to `martingale_bot`
6. Enjoy!
