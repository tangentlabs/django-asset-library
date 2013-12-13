// Set CSRF header when making AJAX requests
// See https://docs.djangoproject.com/en/dev/ref/contrib/csrf/#ajax
//
// To get CSRF token: getCookie('csrftoken')
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        var i = 0;
        for (i; i < cookies.length; i++) {
            var cookie = $.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var asset_library = (function($, ko) {
    var options;

    var getFullUrl = function(urlPart) {
        return options.assetAPIRoot + urlPart;
    };

    var snippets;
    var images;
    var files;

    var SnippetMixin = function() {
        var self = this,
            asset_list;

        this.maxLength = null;

        this.getUrl = function(parameters) {
            return getFullUrl("snippets" + parameters);
        };

        this.setMaxLength = function (maxLength) {
            self.maxLength = maxLength;
        };

        /* Can be snippet used for the current fitting? */
        this.isFit = function (snippet) {
            return this.maxLength === null || snippet.length <= this.maxLength;
        };

        this.useAsset = function (snippet) {
            if (this.isFit(snippet)) {
                $(SnippetMixin.ELEMENT).modal('hide');
                self.callback(snippet.id, snippet.contents);
            }
        };
    };
    SnippetMixin.ELEMENT = '#snippetAssetPopup';

    var ImageMixin = function (allowedExtensions) {
        var self = this,
            asset_list;


        if (!allowedExtensions || allowedExtensions.length === 0) {
            console.warn("No allowed extensions for images, allow any image");
        } else {
            this.allowedExtensions = $.map(allowedExtensions, function (s) { return s.toUpperCase(); });
            this.extensionFilter = allowedExtensions.join();
            this.isAllowedExtension = function (extension) {
                return $.inArray(extension, this.allowedExtensions) >= 0;
            };
        }

        this.fileUploadElement = "#imageupload";

        this.getUrl = function(parameters) {
            return getFullUrl("images" + parameters);
        };

        this.useAsset = function(asset) {
            $.ajax({
                type: "POST",
                url: asset.select_url,
                data: {destination: options.assetPath},
                dataType: "json",
                headers: {'X-CSRFToken': getCookie('csrftoken')},
                error: function () {
                    self.asset_list.error("Can't select image");
                },
                success: function (data) {
                    self.triggerCallback(asset, data.campaign_copy);
                }
            });
        };

        this.triggerCallback = function(asset, campaign_copy) {
            $(ImageMixin.ELEMENT).modal('hide');
            self.callback(asset.id, campaign_copy, asset.width, asset.height);
        };
    };
    ImageMixin.ELEMENT = '#imageAssetPopup';

    var FileMixin = function (allowedExtensions) {
        var self = this,
            asset_list;

        if (!allowedExtensions || allowedExtensions.length === 0) {
            console.warn("No allowed extensions for files, allow any file");
        } else {
            this.allowedExtensions = $.map(allowedExtensions, function (s) { return s.toUpperCase(); });
            this.extensionFilter = allowedExtensions.join();
            this.isAllowedExtension = function (extension) {
                return $.inArray(extension, this.allowedExtensions) >= 0;
            };
        }

        this.fileUploadElement = "#fileupload";

        this.getUrl = function(parameters) {
            return getFullUrl("files" + parameters);
        };

        this.useAsset = function(asset) {
            $.ajax({
                type: "POST",
                url: asset.select_url,
                data: {destination: options.assetPath},
                dataType: "json",
                headers: {'X-CSRFToken': getCookie('csrftoken')},
                error: function () {
                    self.asset_list.error("Can't select file");
                },
                success: function (data) {
                    self.triggerCallback(asset, data.campaign_copy);
                }
            });
        };

        this.triggerCallback = function(asset, campaign_copy) {
            $(FileMixin.ELEMENT).modal('hide');
            self.callback(asset.id, campaign_copy);
        };
    };
    FileMixin.ELEMENT = '#fileAssetPopup';

    var AssetList = function (mixin, allowedExtensions) {
        var self = this;

        /*
         * Mixin takes care about things specific to asset type
         * e.g. images & files need to be copied before selected
         */
        this.mixin = mixin;
        this.mixin.asset_list = self;

        this.viewStyle = ko.observable("grid");
        this.source = ko.observable(null);

        this.tags = ko.observableArray([]);
        this.selectedTag = ko.observable(null);

        this.extensions = ko.observableArray([]);
        this.selectedExtension = ko.observable(null);
        this.allowedExtensions = allowedExtensions;

        this.sort = ko.observable('name');
        this.search = ko.observable(null);

        this.page = ko.observable(1);
        this.limit = ko.observable(20);
        this.pageRange = ko.observableArray([]);
        this.numPages = ko.observable(0);

        this.errorMessage = ko.observable(null);
        /* Encapsulate detail of handling errors.
         * Errors can be handled in different ways, e.g. having list of errors
         * than just a single error.
         */
        this.error = function (message) {
            self.errorMessage(message);
            // Reset view to normal view, e.g. from uploading
            self.status("normal");
        };

        var parametersToUrl = function(parameters) {
            var url_parts = [];
            for (var key in parameters) {
                url_parts.push(key + "=" + parameters[key]);
            }

            if (url_parts.length > 0) {
                return "/?" + url_parts.join('&');
            }
            else {
                return "/";
            }
        };
        var subscription = null;

        var apiParameters = ko.computed(function() {
            var parameters = {};
            if (self.source()) {
                parameters['source'] = self.source();
            }
            if (self.selectedTag()) {
                parameters['tag'] = self.selectedTag();
            }

            if (self.selectedExtension()) {
                parameters['extension'] = self.selectedExtension();
            } else if (self.mixin.extensionFilter) {
                // display only allowed extensions if defined
                parameters['extension'] = self.mixin.extensionFilter;
            }

            if (self.search()) {
                parameters['search'] = self.search();
            }
            parameters['sort_by'] = self.sort();
            parameters['page'] = self.page();
            parameters['limit'] = self.limit();

            return parametersToUrl(parameters);
        }).extend({ throttle: 500 });

        /* Display loading message */
        this.isLoading = ko.observable(true);
        this.status = ko.observable("init");

        /* Assets to display */
        this.assets = ko.observableArray([]);

        /* Display there are no assets message? */
        this.noAssets = ko.computed(function() {
            return !self.isLoading() && self.assets().length == 0;
        });

        this.setPage = function (newPage) {
            self.isLoading(true);
            if (1 <= newPage && newPage <= self.numPages()) {
                self.page(newPage);
            }
        };

        this.incPage = function () {
            if (self.page() < self.numPages()) {
                self.page(self.page() + 1);
            }
        };

        this.decPage = function () {
            if (1 < self.page()) {
                self.page(self.page() - 1);
            }
        };

        /* Return page range for pagination */
        this.getPageRange = function (page, numPages) {
            var i, pageRange = [];

            for (i = 1; i <= numPages; i++) {
                pageRange.push(i);
            }

            return pageRange;
        };

        /* Load data from API */
        this.refresh = function() {
            self.isLoading(true);
            var url = self.mixin.getUrl(apiParameters());
            $.getJSON(url, function(data) {
                self.assets(data['objects']);

                if ('extensions' in data['meta']) {
                    self.extensions(data['meta']['extensions']);
                }

                self.page(data['meta']['page']);
                self.numPages(data['meta']['num_pages']);
                self.pageRange(self.getPageRange(self.page(), self.numPages()));

                self.isLoading(false);
            }).fail(function() {
                self.error("Can't fetch list of assets from server");
            });
        };

        this.prepare = function() {
            if (self.status() != "normal") {
                self.status("normal");
                if (self.mixin.fileUploadElement) {
                    $(self.mixin.fileUploadElement).fileupload(self.fileupload);
                }
            }
            var url = getFullUrl('tags/');
            $.getJSON(url, function(data) {
                self.tags(data['objects']);
            }).fail(function() {
                self.error("Can't fetch list of tags from server");
            });

            if (! subscription) {
                subscription = apiParameters.subscribe(self.refresh);
            }
            self.refresh();
        };

        this.setCallback = function(callback) {
            self.mixin.callback = callback;
        };

        /* Define what happens after selecting asset */
        this.useAsset = mixin.useAsset;

        /* Can this asset used in this context? */
        this.isFit = function (asset) {
            return self.mixin.isFit(asset);
        };

        /* Set maximal length of snippet */
        this.setMaxLength = function (maxLength) {
            return self.mixin.setMaxLength(maxLength);
        }

        this.formatDate = function(dateString) {
            var d = new Date(dateString);
            return d.toLocaleString();
        };

        /* Convert size to human representation */
        this.formatSize = function(size) {
            var unit = 'B';

            if (size >= 1024) {
                size /= 1024;
                unit = 'KB';
            }

            if (size >= 1024) {
                size /= 1024;
                unit = 'MB';
            }

            size = Math.round(size * 10) / 10;
            return size + ' ' + unit;
        };

        /* Extract extension from file name */
        var getExtension = function (filename) {
            filename = filename.toUpperCase();
            return filename.substr(filename.lastIndexOf('.') + 1);
        };

        /*
         * Definition for file upload
         */
        this.fileupload = {
            url: self.mixin.getUrl('/'),
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            // start upload only when file has correct extension
            autoUpload: false,
            /* Permit only certain file extension */
            add: function (e, data) {
                var extension, isAllowed;
                // only single file is permitted to be uploaded
                extension = getExtension(data.files[0].name);
                if (self.mixin.isAllowedExtension(extension)) {
                    // Auto-submit formular for allowed extensions
                    data.process().done(function () {
                        data.submit();
                    });
                } else {
                    self.error("Files with extension " + extension +
                    " are not allowed. Use one of the following file types: " +
                    self.mixin.allowedExtensions.join(', '));
                }
            },
            start: function(e, data) {
                self.status("uploading");
            },
            done: function(e, data) {
                self.mixin.triggerCallback(data.result.object, data.result.campaign_copy);
            },
            error: function() {
                self.error("Oops, can't upload the file");
            }
        };
    };

    return {
        init: function(init_options) {
            var mixin;
            options = init_options;

            /*
             * When applying binding, element can't be undefined, otherwise a nasty
             * bug in Knockout is triggered, see http://jsfiddle.net/imatusov/H6uac/
             */
            var snippetDialog = $(SnippetMixin.ELEMENT)[0];
            if (typeof(snippetDialog) !== "undefined") {
                mixin = new SnippetMixin();
                snippets = new AssetList(mixin);
                ko.applyBindings(snippets, snippetDialog);
            }

            var imageDialog = $(ImageMixin.ELEMENT)[0];
            if (typeof(imageDialog) !== "undefined") {
                mixin = new ImageMixin(options.allowedImageExtensions);
                images = new AssetList(mixin);
                ko.applyBindings(images, imageDialog);
            }

            var fileDialog = $(FileMixin.ELEMENT)[0];
            if (typeof(fileDialog) !== "undefined") {
                mixin = new FileMixin(options.allowedFileExtensions);
                files = new AssetList(mixin);
                ko.applyBindings(files, fileDialog);
            }
        },
        pickSnippetAsset: function(maxLength, callback) {
            if (typeof(snippets) === "undefined") {
                console.error("HTML markup for snippet asset selector not found");
                return;
            }
            snippets.setMaxLength(maxLength);
            snippets.setCallback(callback);
            $(SnippetMixin.ELEMENT).modal('show');
            snippets.prepare();
        },
        pickImageAsset: function(callback) {
            if (typeof(images) === "undefined") {
                console.error("HTML markup for image asset selector not found");
                return;
            }
            images.setCallback(callback);
            $(ImageMixin.ELEMENT).modal('show');
            images.prepare();
        },
        pickFileAsset: function(callback) {
            if (typeof(files) === "undefined") {
                console.error("HTML markup for file asset selector not found");
                return;
            }
            files.setCallback(callback);
            $(FileMixin.ELEMENT).modal('show');
            files.prepare();
        }
    };
})(jQuery, ko);
