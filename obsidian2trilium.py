import argparse
import base64
from pathlib import Path
from queue import Empty, Queue
import re
import shutil
import sys
import tempfile
import threading
import zipfile


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    tmpdir = Path(tempfile.mkdtemp())
    zippath = package_md_notes(
        start_path=args.path,
        tmpdir=tmpdir,
        max_zipper_threads=args.max_zipper_threads,
    )
    if args.output_path:
        output_path = Path(args.output_path).expanduser().resolve()
    else:
        output_path = Path.cwd() / zippath.name

    shutil.move(zippath, output_path)
    shutil.rmtree(tmpdir)
    print(f"Zip file path: '{output_path}'")

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        type=lambda a: Path(a).expanduser().resolve(),
        help="Migration source path.",
    )
    parser.add_argument(
        "--max-zipper-threads",
        default=10,
        type=int,
        help="Run n amount of threads for adding files to the final zip file.",
    )
    parser.add_argument(
        "--output-path", "-o", help="Destination path of the zipped notes."
    )
    return parser.parse_args(argv)


def package_md_notes(
    start_path: Path, tmpdir: Path, max_zipper_threads: int = 10
) -> Path:
    img_regex = re.compile(r"!\[\[([a-zA-Z0-9 \.]+)\]\]", flags=re.M)
    basepath = tmpdir / start_path.name
    zippath = tmpdir / f"{start_path.name}.zip"
    file_queue = Queue()
    stop_event = threading.Event()
    zip_threads: list[threading.Thread] = []
    lock = threading.Lock()
    for _ in range(max_zipper_threads):
        _start_event = threading.Event()
        t = threading.Thread(
            target=do_zipping, args=(lock, _start_event, stop_event, file_queue, zippath)
        )
        t.start()
        _start_event.wait()
        zip_threads.append(t)

    def enqueue_file(p: Path) -> None:
        file_queue.put((p, p.relative_to(tmpdir)))

    img_b64_dict: dict[str, str] = dict(
        (p.name, base64.b64encode(p.read_bytes()).decode("utf-8"))
        for p in start_path.rglob("**/*.png")
    )
    for srcpath in start_path.rglob("**/*.md"):
        dstpath = basepath / srcpath.relative_to(start_path)
        dstpath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(srcpath, dstpath)

        origtext = srcpath.read_text()
        imglinks = img_regex.findall(origtext)
        if not imglinks:
            enqueue_file(dstpath)
            continue

        for imglink in imglinks:
            imgb64 = img_b64_dict.get(imglink)
            if imgb64 is None:
                continue

            # Newlines on both sides will prevent inline images and
            # trilium will interpret multiple newlines as one.
            repl = f"\n\n\n![{srcpath.stem}](data:image/png;base64,{imgb64})\n\n\n"
            origtext = origtext.replace(f"![[{imglink}]]", repl)

        dstpath.write_text(origtext)
        enqueue_file(dstpath)

    stop_event.set()
    for t in zip_threads:
        t.join()
    return zippath


def do_zipping(
    lock: threading.Lock,
    start_event: threading.Event,
    stop_event: threading.Event,
    file_queue: Queue[Path],
    zippath: Path,
) -> None:
    start_event.set()
    while stop_event.is_set() is False or file_queue.empty is False:
        try:
            filepath, arcname = file_queue.get_nowait()
        except Empty:
            continue

        with lock:
            with zipfile.ZipFile(zippath, mode="a") as archive:
                archive.write(filepath, arcname)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
