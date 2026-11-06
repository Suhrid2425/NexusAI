
import asyncio

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

from vercel.blob import (
    put_blob,
    get_blob,
    delete_blob,
    head_blob,
)


def run_async(coroutine):
    return asyncio.run(coroutine)


async def read_blob_stream(pathname):
    result = await get_blob(
        pathname,
        access="private",
    )

    if result is None:
        raise FileNotFoundError(
            f"Blob not found: {pathname}"
        )

    # GetResult.body contains the complete file as bytes.
    return result.body


@deconstructible
class VercelBlobStorage(Storage):

    def _save(self, name, content):
        content.seek(0)

        run_async(
            put_blob(
                name,
                content.read(),
                access="private",
                content_type=getattr(
                    content,
                    "content_type",
                    None,
                ),
            )
        )

        return name

    def _open(self, name, mode="rb"):
        if mode not in ("rb", "r"):
            raise ValueError(
                "VercelBlobStorage supports read-only access."
            )

        data = run_async(
            read_blob_stream(name)
        )

        return ContentFile(data, name=name)

    def delete(self, name):
        run_async(
            delete_blob(name)
        )

    def exists(self, name):
        try:
            run_async(
                head_blob(name)
            )
            return True

        except Exception:
            return False

    def url(self, name):
        raise ValueError(
            "Private documents must be accessed through "
            "the authenticated Django download endpoint."
        )
