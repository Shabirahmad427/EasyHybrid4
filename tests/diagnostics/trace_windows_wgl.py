"""Trace actual GTK WGL bootstrap calls on a Windows CI runner.

Optional diagnostic only: requires Frida and does not replace the uninstrumented
GTK smoke. No native return values or arguments are modified.
"""

import json
import os
from pathlib import Path
import runpy
import sys
import threading


TRACE = r"""
const hooked = new Set();
const observer = Process.attachModuleObserver({
  onAdded(module) {
    if (!/^(gdi32|gdi32full|user32|opengl32|libgallium_wgl|kernel32)\.dll$/i.test(module.name))
      return;
    send({event: 'module', path: module.path});
    const names = ['ChoosePixelFormat', 'SetPixelFormat', 'GetPixelFormat',
      'wglCreateContext', 'wglMakeCurrent', 'glGetString', 'ExitProcess'];
    for (const name of names) {
      const address = module.findExportByName(name);
      if (address === null || hooked.has(address.toString())) continue;
      hooked.add(address.toString());
      Interceptor.attach(address, {
        onEnter(args) {
          this.record = {event: 'call', module: module.path, name: name,
            args: [args[0].toString(), args[1].toString(), args[2].toString()]};
          if (name === 'ExitProcess') {
            send({event: 'exit', code: args[0].toUInt32()});
          }
          if (name === 'ChoosePixelFormat' || name === 'SetPixelFormat') {
            const pfd = args[name === 'ChoosePixelFormat' ? 1 : 2];
            if (!pfd.isNull()) {
              this.record.pfd = {size: pfd.readU16(), version: pfd.add(2).readU16(),
                flags: pfd.add(4).readU32(), colorBits: pfd.add(9).readU8()};
            }
          }
        },
        onLeave(result) {
          this.record.result = result.toString();
          this.record.lastError = this.lastError;
          if (name === 'glGetString' && !result.isNull())
            this.record.text = result.readUtf8String();
          send(this.record);
        }
      });
    }
  }
});
"""


def main():
    if sys.platform != "win32":
        raise SystemExit("WGL tracing requires a native Windows runner")
    import frida

    root = Path(__file__).resolve().parents[2]
    smoke = runpy.run_path(str(root / "tests/test_gtk_icon_theme_smoke.py"))["_GTK_SMOKE"]
    environment = dict(os.environ, G_DEBUG="fatal-criticals")
    device = frida.get_local_device()
    done = threading.Event()
    result = {"exit_code": None, "trace_errors": []}

    def output(pid, fd, data):
        if data:
            print(data.decode("utf-8", errors="replace"), end="", flush=True)

    def message(value, data):
        if value["type"] == "send":
            record = value["payload"]
            if record.get("event") == "exit":
                result["exit_code"] = record["code"]
            print("WGL_TRACE=" + json.dumps(record), flush=True)
        else:
            result["trace_errors"].append(value)
            print("WGL_TRACE_ERROR=" + json.dumps(value), flush=True)

    def detached(reason, crash=None):
        print("WGL_TRACE_DETACHED=" + reason, flush=True)
        done.set()

    device.on("output", output)
    pid = device.spawn([sys.executable, "-u", "-c", smoke],
                       env=environment, cwd=str(root), stdio="pipe")
    try:
        session = device.attach(pid)
        session.on("detached", detached)
        script = session.create_script(TRACE)
        script.on("message", message)
        script.load()
        device.resume(pid)
        if not done.wait(45):
            raise TimeoutError("GTK WGL trace exceeded 45 seconds")
    finally:
        if not done.is_set():
            device.kill(pid)
    print("WGL_TRACE_RESULT=" + json.dumps(result), flush=True)
    return 1 if result["trace_errors"] else (result["exit_code"] or 0)


if __name__ == "__main__":
    raise SystemExit(main())
