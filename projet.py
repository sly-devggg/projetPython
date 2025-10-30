import os
import re
import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin

def nettoyer_nom_fichier(s):
    return re.sub(r'[<>:"/\\|?*#]', '_', s.strip()) # Remplace les caractères interdits par des underscores

class LivresSpider(scrapy.Spider):
    name = "livres"
    start_urls = ["https://books.toscrape.com/"]

    def demarrer(self, response):
        # Récupère les liens de toutes les catégories
        for cat in response.css('div.side_categories ul li ul li a'):
            nom_categorie = cat.css('::text').get().strip()
            url_categorie = urljoin(response.url, cat.attrib['href'])
            yield scrapy.Request(
                url_categorie,
                callback=self.parcourir_categorie,
                meta={'categorie': nom_categorie}
            )

    def parcourir_categorie(self, response):
       # Parcourt les livres dans une catégorie et gère la pagination
        nom_categorie = response.meta['categorie']

        for livre in response.css('h3 a'):
            url_livre = urljoin(response.url, livre.attrib['href'])
            yield scrapy.Request(
                url_livre,
                callback=self.parcourir_livre,
                meta={'categorie': nom_categorie}
            )

        page_suivante = response.css('li.next a::attr(href)').get()
        if page_suivante:
            yield scrapy.Request(
                urljoin(response.url, page_suivante),
                callback=self.parcourir_categorie,
                meta={'categorie': nom_categorie}
            )

    def parcourir_livre(self, response):
        # Extrait les informations du livre
        categorie = response.meta['categorie']
        titre = response.css('h1::text').get().strip()
        prix = response.css('p.price_color::text').get()
        disponibilite = response.css('p.availability::text').re_first(r'\w+')
        note = response.css('p.star-rating::attr(class)').re_first(r'star-rating (\w+)')
        upc = response.css('table tr:nth-child(1) td::text').get()

        image_rel = response.css('div.item.active img::attr(src)').get()
        url_image = urljoin(response.url, image_rel)

        dossier_image = os.path.join('outputs', 'images', categorie)
        os.makedirs(dossier_image, exist_ok=True)
        chemin_image = os.path.join(dossier_image, f"{nettoyer_nom_fichier(titre)}.jpg")

        # Téléchargement de l'image
        yield scrapy.Request(
            url_image,
            callback=self.sauvegarder_image,
            meta={'path': chemin_image},
            dont_filter=True
        )

        # Données à écrire dans le CSV
        yield {
            'titre': titre,
            'prix': prix,
            'disponibilite': disponibilite,
            'note': note,
            'upc': upc,
            'categorie': categorie,
            'url_page_produit': response.url,
            'url_image': url_image,
            'chemin_image': chemin_image
        }

    def sauvegarder_image(self, response):
        # Sauvegarde l'image téléchargée
        with open(response.meta['path'], 'wb') as f:
            f.write(response.body)

if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    process = CrawlerProcess(settings={
        "FEEDS": {"outputs/livres.csv": {"format": "csv"}},
        "LOG_LEVEL": "INFO",
        "USER_AGENT": "Mozilla/5.0 (compatible; LivresBot/1.0)"
    })
    process.crawl(LivresSpider)
    process.start()
