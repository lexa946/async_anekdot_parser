import asyncio
import aiohttp
from datetime import datetime

from pydantic import BaseModel
from bs4 import BeautifulSoup


class SAuthor(BaseModel):
    name: str
    link: str


class SAnekdot(BaseModel):
    text: str
    author: SAuthor | None


main_host = "https://www.anekdot.ru"
main_url = "https://www.anekdot.ru/release/anekdot/day"



async def parse_day(date: datetime) -> list[SAnekdot]:
    """
        Асинхронно запрашиваем страницы
    """
    async with aiohttp.ClientSession() as session:
        session.headers[
            'User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        url = main_url + "/" + date.strftime("%Y-%m-%d")
        print("Парсинг страницы:", url)
        async with session.get(url) as response:
            response_text = await response.text()

            soup = BeautifulSoup(response_text, "lxml")
        return get_anekdots(soup)


def get_anekdots(soup: BeautifulSoup) -> list[SAnekdot]:
    """
        Получаем все андекдоты со страницы

    """
    boxes = soup.select(".topicbox")
    anekdots = []
    for box in boxes:
        author_tag = box.select_one(".topicbox a.auth")
        if author_tag:
            link = author_tag.get("href", "")
            if "http" not in link:
                link = main_host + link
            author = SAuthor(name=author_tag.text, link=link) if author_tag else None
        else:
            author = None
        text_tag = box.select_one('.text')
        if not text_tag: continue
        anekdots.append(SAnekdot(text=text_tag.text, author=author))
    return anekdots


async def send_to_base(text, author_name, author_link):
    async with aiohttp.ClientSession() as session:
        text_to_Print = text[:20] + "..."
        print("Добавляю анекдот:", text_to_Print, "Автор", author_name )
        await session.post("http://127.0.0.1:8082/anekdot/api/anekdot/", json={
            "text": text,
            "author": {
                "name": author_name,
                "link": author_link,
            }
        })




async def main():
    dates = [datetime(2024, 8, i) for i in range(1, 20)]

    tasks = [asyncio.create_task(parse_day(date)) for date in dates]
    result = await asyncio.gather(*tasks)

    for row in result:
        tasks = []
        for anekdot in row:
            if anekdot.author:
                tasks.append(asyncio.create_task(send_to_base(anekdot.text, anekdot.author.name, anekdot.author.link)))
            else:
                tasks.append(asyncio.create_task(send_to_base(anekdot.text, None, None)))

        await asyncio.gather(*tasks)



if __name__ == '__main__':
    asyncio.run(main())
