"""Create missing local settings; never replace existing credentials."""
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]


def configure():
    for name in (".env.fastbase", ".infra.env"):
        target = ROOT / name
        if not target.exists():
            target.write_text((ROOT / (name + ".example")).read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Created {name}; fill database credentials in .infra.env")
    target = ROOT / ".core-package.env"
    if not target.exists():
        with target.open("x", encoding="utf-8") as stream:
            stream.write(f"CORE_JWT_SECRET={secrets.token_hex(32)}\nCORE_ACCESS_TOKEN_MINUTES=30\nCORE_REFRESH_TOKEN_DAYS=7\nCORE_BCRYPT_ROUNDS=12\n")
        print("Created .core-package.env with a generated local JWT secret")


if __name__ == "__main__":
    configure()
