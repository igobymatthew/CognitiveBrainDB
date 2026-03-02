from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from cognitivebrain.models.base import Base
from cognitivebrain.models.entities import Activation, Mode


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    dbapi_connection.execute("PRAGMA foreign_keys=ON")


def test_deleting_mode_cascades_to_activation():
    engine = create_engine("sqlite:///:memory:")
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        mode = Mode(
            name="focus",
            description="test mode",
            vec_base=[0.0] * 1536,
            vec_current=[0.0] * 1536,
        )
        session.add(mode)
        session.flush()

        activation = Activation(mode_id=mode.id, chunk_id=None, score=0.42)
        session.add(activation)
        session.commit()

        session.delete(mode)
        session.commit()

        remaining = session.scalars(select(Activation)).all()

    assert remaining == []
