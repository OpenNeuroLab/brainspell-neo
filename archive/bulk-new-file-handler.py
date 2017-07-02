"""
 class BulkNewFileHandler(BaseHandler, torngithub.GithubMixin):
     @tornado.web.asynchronous
     @tornado.gen.coroutine
     def post(self):
         startime = time.time()
         collection = self.get_argument("collection")
         pmids = self.get_argument("pmids")
         pmids = eval(pmids)
         user_info = self.__get_current_github_object__()["login"]
         if collection in next(User.select().where(User.username == user_info).execute()).collections: #If collection exists
             collection = "brainspell-collection-" + collection
             for pmid in pmids:
                 pmid = eval(pmid)
                 article = list(get_article(pmid))[0]
                 entry = {"pmid": pmid,
                         "title": article.title,
                         "reference": article.reference,
                         "doi": article.doi,
                          "notes": "Here are my notes on this article"}
                 content = b64encode(json_encode(entry).encode("utf-8")).decode('utf-8')
                 gh_user = self.__get_current_github_object__()
                 add_to_repo(collection,pmid,self.get_current_github_username())
                 body = {
                     "message": "adding {} to collection".format(pmid),
                     "content": content
                 }
                 ress = yield [
                     torngithub.github_request(
                         self.get_auth_http_client(),
                         '/repos/{owner}/{repo}/contents/{path}'.format(owner=self.get_current_github_username(),
                                                                        repo=collection,
                                                                        path="{}.json".format(pmid)),
                         access_token=self.get_current_github_access_token(),
                         method="PUT",
                         body=body
                     )
                 ]
                 data = []
                 for res in ress:
                     data.extend(res.body)
                 endtime = time.time()
         else:
             print("Your collection doesn't exist")
             return False #TODO: Tell user the collection doesn't exist
"""
