import scrapy
import os
from urllib.parse import urljoin
from scrapy.crawler import CrawlerProcess

# petite fonction pour éviter les caractères bizarres dans les noms de fichiers
def clean_nom(nom):
    return nom.replace('/', '_').replace(':', '').replace('?', '').strip()

class BookSpider(scrapy.Spider):
    name = 'books'
    start_urls = ['https://books.toscrape.com']

    def parse(self, response):
        # récup toutes les catégories sur la gauche
        cats = response.css('.side_categories ul li ul li a')
        for c in cats:
            titre = c.css('::text').get().strip()
            lien = urljoin(response.url, c.attrib['href'])
            # on passe le nom de la catégorie dans les meta
            yield scrapy.Request(lien, callback=self.parse_cat, meta={'cat': titre})

    def parse_cat(self, response):
        cat = response.meta['cat']
        livres = response.css('h3 a')
        for l in livres:
            link = urljoin(response.url, l.attrib['href'])
            yield scrapy.Request(link, callback=self.parse_book, meta={'cat': cat})

        # vérifie s’il y a une page suivante
        nextpage = response.css('.next a::attr(href)').get()
        if nextpage:
            url_suiv = urljoin(response.url, nextpage)
            yield scrapy.Request(url_suiv, callback=self.parse_cat, meta={'cat': cat})

    def parse_book(self, response):
        cat = response.meta['cat']
        titre = response.css('h1::text').get()
        prix = response.css('.price_color::text').get()
        dispo = response.css('.availability::text').getall()
        dispo = ''.join([d.strip() for d in dispo if d.strip()])  # nettoie les espaces inutiles
        note = response.css('p.star-rating::attr(class)').re_first('star-rating (\w+)')
        upc = response.css('table tr td::text').get()

        # récupère l’image du livre
        img_src = response.css('div.item.active img::attr(src)').get()
        img_url = urljoin(response.url, img_src)

        dossier = f"outputs/img/{cat}"
        os.makedirs(dossier, exist_ok=True)
        fichier_img = os.path.join(dossier, clean_nom(titre) + ".jpg")

        # télécharge l’image
        yield scrapy.Request(img_url, callback=self.save_img, meta={'fichier': fichier_img}, dont_filter=True)

        yield {
            'titre': titre,
            'prix': prix,
            'dispo': dispo,
            'note': note,
            'upc': upc,
            'categorie': cat,
            'url': response.url
        }

    def save_img(self, response):
        with open(response.meta['fichier'], 'wb') as f:
            f.write(response.body)
        # print juste pour vérifier que ça marche
        print(f"Image sauvegardée : {response.meta['fichier']}")


if __name__ == '__main__':
    if not os.path.exists('outputs'):
        os.mkdir('outputs')

    process = CrawlerProcess(settings={
        'FEEDS': {'outputs/livres.csv': {'format': 'csv'}},
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64)'
    })
    process.crawl(BookSpider)
    process.start()