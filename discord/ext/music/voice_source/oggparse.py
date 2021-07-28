import struct

from discord.errors import DiscordException

__all__ = (
    'OggError',
    'OggPage',
    'OggStream',
)


class OggError(DiscordException):
    """An exception that is thrown for Ogg stream parsing errors."""
    pass

# https://tools.ietf.org/html/rfc3533
# https://tools.ietf.org/html/rfc7845

class AsyncOggPage:
    _header = struct.Struct('<xBQIIIB')

    def __init__(self, stream):
        self.stream = stream

    async def _parse_packets(self):
        stream = self.stream
        try:
            header = await stream.read(struct.calcsize(self._header.format))

            self.flag, self.gran_pos, self.serial, \
            self.pagenum, self.crc, self.segnum = self._header.unpack(header)

            self.segtable = await stream.read(self.segnum)
            bodylen = sum(struct.unpack('B'*self.segnum, self.segtable))
            self.data = await stream.read(bodylen)
        except Exception:
            raise OggError('bad data stream') from None

    async def iter_packets(self):
        await self._parse_packets()
        packetlen = offset = 0
        partial = True

        for seg in self.segtable:
            if seg == 255:
                packetlen += 255
                partial = True
            else:
                packetlen += seg
                yield self.data[offset:offset+packetlen], True
                offset += packetlen
                packetlen = 0
                partial = False

        if partial:
            yield self.data[offset:], False

class AsyncOggStream:
    def __init__(self, stream):
        self.stream = stream
        self.partial = b''

    async def _next_page(self):
        head = await self.stream.read(4)
        if head == b'OggS':
            return AsyncOggPage(self.stream)
        elif not head:
            return None
        else:
            raise OggError('invalid header magic')

    async def _iter_pages(self):
        page = await self._next_page()
        while page:
            yield page
            page = await self._next_page()

    async def iter_packets(self):
        partial = b''
        async for page in self._iter_pages():
            async for data, complete in page.iter_packets():
                partial += data
                if complete:
                    yield partial
                    partial = b''