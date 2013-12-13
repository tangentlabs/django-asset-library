# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Tag'
        db.create_table(u'asset_library_tag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
        ))
        db.send_create_signal(u'asset_library', ['Tag'])

        # Adding model 'Asset'
        db.create_table(u'asset_library_asset', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('date_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('is_global', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('shared_by', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='shared_assets', null=True, to=orm['auth.User'])),
        ))
        db.send_create_signal(u'asset_library', ['Asset'])

        # Adding M2M table for field tags on 'Asset'
        m2m_table_name = db.shorten_name(u'asset_library_asset_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('asset', models.ForeignKey(orm[u'asset_library.asset'], null=False)),
            ('tag', models.ForeignKey(orm[u'asset_library.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['asset_id', 'tag_id'])

        # Adding model 'ImageAsset'
        db.create_table(u'asset_library_imageasset', (
            (u'asset_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['asset_library.Asset'], unique=True, primary_key=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('width', self.gf('django.db.models.fields.IntegerField')()),
            ('height', self.gf('django.db.models.fields.IntegerField')()),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
            ('extension', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('copyright_holder', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('copyright_date', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal(u'asset_library', ['ImageAsset'])

        # Adding model 'SnippetAsset'
        db.create_table(u'asset_library_snippetasset', (
            (u'asset_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['asset_library.Asset'], unique=True, primary_key=True)),
            ('contents', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'asset_library', ['SnippetAsset'])

        # Adding model 'FileAsset'
        db.create_table(u'asset_library_fileasset', (
            (u'asset_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['asset_library.Asset'], unique=True, primary_key=True)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('size', self.gf('django.db.models.fields.IntegerField')()),
            ('extension', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'asset_library', ['FileAsset'])


    def backwards(self, orm):
        # Deleting model 'Tag'
        db.delete_table(u'asset_library_tag')

        # Deleting model 'Asset'
        db.delete_table(u'asset_library_asset')

        # Removing M2M table for field tags on 'Asset'
        db.delete_table(db.shorten_name(u'asset_library_asset_tags'))

        # Deleting model 'ImageAsset'
        db.delete_table(u'asset_library_imageasset')

        # Deleting model 'SnippetAsset'
        db.delete_table(u'asset_library_snippetasset')

        # Deleting model 'FileAsset'
        db.delete_table(u'asset_library_fileasset')


    models = {
        u'asset_library.asset': {
            'Meta': {'object_name': 'Asset'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_global': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'shared_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'shared_assets'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'assets'", 'symmetrical': 'False', 'to': u"orm['asset_library.Tag']"})
        },
        u'asset_library.fileasset': {
            'Meta': {'object_name': 'FileAsset', '_ormbases': [u'asset_library.Asset']},
            u'asset_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['asset_library.Asset']", 'unique': 'True', 'primary_key': 'True'}),
            'extension': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'size': ('django.db.models.fields.IntegerField', [], {})
        },
        u'asset_library.imageasset': {
            'Meta': {'object_name': 'ImageAsset', '_ormbases': [u'asset_library.Asset']},
            u'asset_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['asset_library.Asset']", 'unique': 'True', 'primary_key': 'True'}),
            'copyright_date': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'copyright_holder': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'extension': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        u'asset_library.snippetasset': {
            'Meta': {'object_name': 'SnippetAsset', '_ormbases': [u'asset_library.Asset']},
            u'asset_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['asset_library.Asset']", 'unique': 'True', 'primary_key': 'True'}),
            'contents': ('django.db.models.fields.TextField', [], {})
        },
        u'asset_library.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['asset_library']