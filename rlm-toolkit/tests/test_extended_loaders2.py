"""Tests for extended loaders part 2."""

import pytest


class TestExtendedLoaders2Import:
    """Test extended loaders part 2 can be imported."""
    
    def test_import_imap(self):
        from rlm_toolkit.loaders.extended2 import IMAPLoader
        assert IMAPLoader is not None
    
    def test_import_outlook(self):
        from rlm_toolkit.loaders.extended2 import OutlookLoader
        assert OutlookLoader is not None
    
    def test_import_image(self):
        from rlm_toolkit.loaders.extended2 import ImageLoader
        assert ImageLoader is not None
    
    def test_import_audio(self):
        from rlm_toolkit.loaders.extended2 import AudioLoader
        assert AudioLoader is not None
    
    def test_import_video(self):
        from rlm_toolkit.loaders.extended2 import VideoLoader
        assert VideoLoader is not None
    
    def test_import_subtitle(self):
        from rlm_toolkit.loaders.extended2 import SubtitleLoader
        assert SubtitleLoader is not None
    
    def test_import_postgresql(self):
        from rlm_toolkit.loaders.extended2 import PostgreSQLLoader
        assert PostgreSQLLoader is not None
    
    def test_import_mysql(self):
        from rlm_toolkit.loaders.extended2 import MySQLLoader
        assert MySQLLoader is not None
    
    def test_import_sqlite(self):
        from rlm_toolkit.loaders.extended2 import SQLiteLoader
        assert SQLiteLoader is not None
    
    def test_import_cassandra(self):
        from rlm_toolkit.loaders.extended2 import CassandraLoader
        assert CassandraLoader is not None
    
    def test_import_neo4j(self):
        from rlm_toolkit.loaders.extended2 import Neo4jLoader
        assert Neo4jLoader is not None
    
    def test_import_clickhouse(self):
        from rlm_toolkit.loaders.extended2 import ClickHouseLoader
        assert ClickHouseLoader is not None
    
    def test_import_dynamodb(self):
        from rlm_toolkit.loaders.extended2 import DynamoDBLoader
        assert DynamoDBLoader is not None
    
    def test_import_firestore(self):
        from rlm_toolkit.loaders.extended2 import FirestoreLoader
        assert FirestoreLoader is not None
    
    def test_import_restapi(self):
        from rlm_toolkit.loaders.extended2 import RESTAPILoader
        assert RESTAPILoader is not None
    
    def test_import_graphql(self):
        from rlm_toolkit.loaders.extended2 import GraphQLLoader
        assert GraphQLLoader is not None
    
    def test_import_rss(self):
        from rlm_toolkit.loaders.extended2 import RSSLoader
        assert RSSLoader is not None
    
    def test_import_odata(self):
        from rlm_toolkit.loaders.extended2 import ODataLoader
        assert ODataLoader is not None
    
    def test_import_sharepoint(self):
        from rlm_toolkit.loaders.extended2 import SharePointLoader
        assert SharePointLoader is not None
    
    def test_import_zendesk(self):
        from rlm_toolkit.loaders.extended2 import ZendeskLoader
        assert ZendeskLoader is not None
    
    def test_import_intercom(self):
        from rlm_toolkit.loaders.extended2 import IntercomLoader
        assert IntercomLoader is not None
    
    def test_import_freshdesk(self):
        from rlm_toolkit.loaders.extended2 import FreshdeskLoader
        assert FreshdeskLoader is not None


class TestSQLiteLoaderFunction:
    """Test SQLite loader works."""
    
    def test_sqlite_loader(self):
        import tempfile
        import sqlite3
        
        from rlm_toolkit.loaders.extended2 import SQLiteLoader
        
        # Create temp database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'item1')")
        conn.execute("INSERT INTO test VALUES (2, 'item2')")
        conn.commit()
        conn.close()
        
        # Test loader
        loader = SQLiteLoader(db_path, "SELECT * FROM test")
        docs = loader.load()
        
        assert len(docs) == 2


class TestTotalEcosystemCount:
    """Verify total ecosystem integration count."""
    
    def test_has_extended_loaders(self):
        from rlm_toolkit.loaders import extended
        assert hasattr(extended, "HubSpotLoader")
    
    def test_has_extended_loaders2(self):
        from rlm_toolkit.loaders import extended2
        assert hasattr(extended2, "PostgreSQLLoader")
    
    def test_has_extended_vectorstores(self):
        from rlm_toolkit.vectorstores import extended
        assert hasattr(extended, "RedisVectorStore")
    
    def test_has_extended_tools(self):
        from rlm_toolkit.tools import extended
        assert hasattr(extended, "OpenWeatherMapTool")
