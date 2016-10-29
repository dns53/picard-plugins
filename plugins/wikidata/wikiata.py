PLUGIN_NAME = 'wikidata-genre'
PLUGIN_AUTHOR = 'Daniel Sobey'
PLUGIN_DESCRIPTION = 'query wikidata to get genre tags'
PLUGIN_VERSION = '0.1'
PLUGIN_API_VERSIONS = ["0.9.0", "0.10", "0.15"]

from picard import config, log
from picard.metadata import register_album_metadata_processor
from picard.webservice import XmlWebService
from functools import partial

class wikidata:
    def process(self,tagger, metadata, release):
        self.xmlws=tagger.tagger.xmlws
        self.log=tagger.log
        release_id = dict.get(metadata,'musicbrainz_releasegroupid')[0]
        # find the wikidata url if this exists
        host = config.setting["server_host"]
        port = config.setting["server_port"]
        path = '/ws/2/release-group/%s?inc=url-rels' % release_id
        
        self.xmlws.get(host, port, path,
                       partial(self.website_process, release_id,metadata),
                                xml=True, priority=False, important=False)

    
    def website_process(self,release_id,metadata, response, reply, error):
	if error:
            log.info('WIKIDATA: error retrieving release group info')
        else:
            if 'metadata' in response.children:
                if 'release_group' in response.metadata[0].children:
                    if 'relation_list' in response.metadata[0].release_group[0].children:
                        for relation in response.metadata[0].release_group[0].relation_list[0].relation:
                            if relation.type == 'wikidata' and 'target' in relation.children:
                                wikidata_url=relation.target[0].text
                                self.process_wikidata(wikidata_url,metadata)
    def process_wikidata(self,wikidata_url,metadata):
        item=wikidata_url.split('/')[4]
        path="/wiki/Special:EntityData/"+item+".rdf"
        log.info('WIKIDATA: fetching the folowing url wikidata.org%s' % path)
        self.xmlws.get('www.wikidata.org', 443, path,
                       partial(self.parse_wikidata_response, item,metadata),
                                xml=True, priority=False, important=False)
    def parse_wikidata_response(self,item,metadata, response, reply, error):
        genre_entries=[]
        genre_list=[]
        if error:
            log.error('WIKIDATA: error getting data from wikidata.org')
        else:
            if 'RDF' in response.children:
                node = response.RDF[0]
                for node1 in node.Description:
                    if 'about' in node1.attribs:
                        if node1.attribs.get('about') == 'http://www.wikidata.org/entity/%s' % item:
                            for key,val in node1.children.items():
                                if key=='P136':
                                    for i in val:
                                        if 'resource' in i.attribs:
                                            tmp=i.attribs.get('resource')
                                            if 'entity' ==tmp.split('/')[3] and len(tmp.split('/'))== 5:
                                                genre_id=tmp.split('/')[4]
                                                log.info('WIKIDATA: Found the wikidata id for the genre: %s' % genre_id)
                                                genre_entries.append(tmp)
                        else:
                            for tmp in genre_entries:
                                if tmp == node1.attribs.get('about'):
                                    list1=node1.children.get('name')
                                    for node2 in list1:
                                        if node2.attribs.get('lang')=='en':
                                            genre=node2.text
                                            genre_list.append(genre)
                                            log.debug('Our genre is: %s' % genre)
        if len(genre_list) > 0:
            log.info('WiKIDATA: final list of wikidata id found: %s' % genre_entries)
            log.info('WIKIDATA: final list of genre: %s' % genre_list)
            metadata["genre"] = genre_list
        else:
            print 'Genre not found in wikidata'

register_album_metadata_processor(wikidata().process)

