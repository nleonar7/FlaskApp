"""Build a slim SQLite DB for a PythonAnywhere (free-tier) deploy.

The working DB is ~820 MB, almost all of it the PLUTO `raw_payload` JSON blob
(~648 MB). PythonAnywhere's free tier gives 512 MB of disk *and* can't reach
the internet to re-load the data, so we produce a trimmed copy locally and
upload it:

  * drops `raw_payload` (the app never reads it at runtime)
  * optionally keeps only some boroughs
  * VACUUMs to reclaim the freed space

Usage:
    python scripts/build_demo_db.py                      # all boroughs, no raw
    python scripts/build_demo_db.py --boroughs SI        # Staten Island only
    python scripts/build_demo_db.py --source instance/posts.db --dest demo.db
"""

import argparse
import os
import shutil
import sqlite3


def build(source: str, dest: str, boroughs: list[str] | None) -> None:
    if not os.path.exists(source):
        raise SystemExit(f'source DB not found: {source}')
    if os.path.abspath(source) == os.path.abspath(dest):
        raise SystemExit('dest must differ from source')

    print(f'copying {source} -> {dest} ...')
    shutil.copyfile(source, dest)

    conn = sqlite3.connect(dest)
    try:
        before = conn.execute('select count(*) from nyc_pluto_lot').fetchone()[0]

        if boroughs:
            placeholders = ','.join('?' for _ in boroughs)
            conn.execute(
                f'delete from nyc_pluto_lot where borough not in ({placeholders})',
                boroughs,
            )
            print(f'kept boroughs {boroughs}')

        # Drop the heavy blob the web app never reads.
        conn.execute('update nyc_pluto_lot set raw_payload = null')
        conn.commit()

        after = conn.execute('select count(*) from nyc_pluto_lot').fetchone()[0]
        print(f'pluto rows: {before:,} -> {after:,}')
        print('vacuuming ...')
        conn.execute('vacuum')
        conn.commit()
    finally:
        conn.close()

    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f'done: {dest} is {size_mb:.1f} MB')
    if size_mb > 480:
        print('WARNING: still close to the 512 MB free-tier limit; '
              'consider --boroughs SI to shrink further.')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', default='instance/posts.db')
    ap.add_argument('--dest', default='demo_posts.db')
    ap.add_argument('--boroughs', nargs='*', default=None,
                    help="borough codes to keep (e.g. SI BK); default keeps all")
    args = ap.parse_args()
    build(args.source, args.dest, args.boroughs)


if __name__ == '__main__':
    main()
