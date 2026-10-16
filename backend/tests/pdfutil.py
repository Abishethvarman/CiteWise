import pymupdf


def pdf_bytes(pages: list[str]) -> bytes:
    document = pymupdf.open()
    try:
        if not pages:
            return document.tobytes()
        for body in pages:
            page = document.new_page(width=595, height=842)
            y = 72
            for line in body.split("\n"):
                page.insert_text((72, y), line[:140], fontsize=11, fontname="helv")
                y += 16
                if y > 800:
                    break
        return document.tobytes()
    finally:
        document.close()
