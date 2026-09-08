# Third-party licences

This project is MIT ([LICENSE](LICENSE)). No third-party source is vendored
into this repository; the list below covers what it depends on at runtime.

## mihai-dinculescu/tapo (MIT)

https://github.com/mihai-dinculescu/tapo

The sole runtime dependency. Provides `ApiClient` and the P110 handler used to
switch the plug. Verified against the licence file shipped in the installed
wheel (`tapo-0.8.10.dist-info/licenses/LICENSE`):

```
MIT License

Copyright (c) 2022-2025 Mihai Dinculescu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## System tools

`upower` and `/sys/class/power_supply` are read through the OS; neither is
redistributed here.

## Trademark

Tapo is a trademark of TP-Link. This project is not affiliated with, endorsed
by, or vetted by TP-Link, and `tapo` is an unofficial client.
