import scrapy
import json,re

class ProductSpider(scrapy.Spider):
    name = "product1"
    allowed_domains = ["crateandbarrel.me"]
    start_urls = ["https://api.crateandbarrel.me/rest/v2/cab/categories/tabletop-bar-2?fields=FULL&lang=en&curr=AED"]
    headers = {
        'X-Anonymous-Consents': '%5B%5D',
        'Accept': 'application/json, text/plain, */*',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'Referer': 'https://www.crateandbarrel.me/',
        'sec-ch-ua-mobile': '?0',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(url, headers=self.headers, callback=self.parse)

    def parse(self, response):
        category_datas = json.loads(response.text)
        for category_data in category_datas["subCategories"]:
            category_link = category_data['url'].split('/')[-1]
            links = f'https://api.crateandbarrel.me/rest/v2/cab/categories/{category_link}?fields=FULL&lang=en&curr=AED'
            yield scrapy.Request(links, callback=self.parse_category, headers=self.headers)

    def parse_category(self, response):
        sub_cat_datas = json.loads(response.text)
        for sub_cat_data in sub_cat_datas["subCategories"]:
            ids1 = sub_cat_data['url'].split('/')[-1]
            url = f"https://api.crateandbarrel.me/rest/v2/cab/products/search?fields=keywordRedirectUrl%2Cproducts(code%2CearnablePoints%2Csellable%2Cname%2CurlName%2Csummary%2Cprice(FULL)%2Cbadges(code%2Cname)%2Cimages(DEFAULT)%2Cstock(FULL)%2CaverageRating%2CcrossedPrice(FULL)%2Ccategories(name%2Ccode%2Curl)%2Cswatches(FULL)%2Cvariants(FULL)%2CprimaryCategory(FULL))%2Cfacets%2Cpagination(DEFAULT)%2Csorts(DEFAULT)%2CfreeTextSearch&query=%3Arelevance%3AallCategories%3A{ids1}&pageSize=24&lang=en&curr=AED"
            yield scrapy.Request(url, callback=self.parse_product_list, headers=self.headers)

    def parse_product_list(self, response):
        cat_data = json.loads(response.text)
        products = cat_data.get('products', [])
        for product in products:
            product_id = product['code']
            url = f"https://api.crateandbarrel.me/rest/v2/cab/products/{product_id}?fields=FULL,classifications(FULL),variants(FULL),urlName,price(FULL,formattedValue),crossedPrice(FULL),productReferences(target(images(BASIC),urlName,price,crossedPrice(FULL))),code,name,summary,images(DEFAULT,galleryIndex),baseProduct&lang=en&curr=AED"
            yield scrapy.Request(url, callback=self.parse_product, headers=self.headers)

    def parse_product(self, response):
        data = json.loads(response.text)
        product_name = data['urlName']
        stock = data['stock']['stockLevel']
        breadcrumbs = [br['name'] for br in data.get('breadcrumbs', [])[2:]]
        breadcrumb = '> '.join(breadcrumbs)
        original_price = data.get('crossedPrice', {}).get('value', data['price']['value'])
        discount_price = data['price']['value']
        product_dimension = []
        descriptions = []
        images = data.get('images', [])
        image_url = [f"https://api.crateandbarrel.me/{img['url']}" for img in images if '1440x960' in img.get('url', '')]

        for des in data.get('classifications', []):
            if 'dimensions-dat' in des['code']:
                dimensions = des['features'][0]
                feature_name = dimensions['name']
                value = dimensions['featureValues'][0]['value']
                unit = dimensions.get('featureUnit', {}).get('symbol', '') 
                dimension = f"{des['code'].split('-')[-1]}: {feature_name}-{value} {unit}"
                product_dimension.append(dimension)

            if 'cab-global-features' in des['code']:
                values = des['features']
                for value in values:
                    if 'cab-global-features.details' in value['code']:
                        desc = value['featureValues'][0]['value']
                        clean_value = scrapy.Selector(text=desc).xpath('//text()').get()
                        descriptions.append(clean_value.strip())

        main_category = data.get('breadcrumbs', [])[3:4][0].get('name', '')
        sub_category = data.get('breadcrumbs', [])[4:5][0].get('name', '')
        product_url = f"https://www.crateandbarrel.me/en-ae{data['url']}"

        yield {
            'product_url': product_url,
            'product_name': product_name,
            'breadcrumb': breadcrumb,
            'original_price': original_price,
            'discount_price': discount_price,
            'main_category': main_category,
            'sub_category': sub_category,
            'product_dimension': product_dimension,
            'clean_descriptions': descriptions,
            'image_url': image_url,
            'stock': stock
        }
