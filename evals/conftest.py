import aiosqlite
import pytest
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

RESULTS = pytest.StashKey[list]()


def pytest_addoption(parser):
    parser.addoption("--runs", type=int, default=3, help="прогонов на сценарий, k в pass^k")


def pytest_configure(config):
    config.stash[RESULTS] = []


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def runs(request) -> int:
    return request.config.getoption("--runs")


@pytest.fixture(scope="session")
def results(request) -> list:
    return request.config.stash[RESULTS]


@pytest.fixture(scope="session")
async def aclient():
    async with AsyncOpenAI(max_retries=5, timeout=120) as client:
        yield client


@pytest.fixture(scope="session")
async def chunks(tmp_path_factory, aclient) -> list[dict]:
    from src.database import open_db
    from src.repositories.document import DocumentRepository
    from src.services.document import DocumentService

    async with aiosqlite.connect(tmp_path_factory.mktemp("index") / "docs.db") as db:
        await open_db(db)
        repository = DocumentRepository(db)
        await DocumentService(repository, aclient).index()
        return await repository.list_chunks()


def pytest_terminal_summary(terminalreporter, config):
    results = config.stash.get(RESULTS, [])
    if not results:
        return
    k = config.getoption("--runs")
    write = terminalreporter.write_line
    terminalreporter.section(f"сценарии агента, pass^{k}")
    write(f"{'id':6} {'kind':14} {'pass':>6} {'steps':>6} {'$':>9}")
    for r in results:
        cost = f"{r['cost']:.5f}" if r["cost"] is not None else "-"
        write(f"{r['id']:6} {r['kind']:14} {r['passed']:>4}/{k} {r['steps']:6.1f} {cost:>9}")
    full = sum(r["passed"] == k for r in results)
    write(f"pass^{k} = {full}/{len(results)} = {full / len(results):.2f}")
