/*global document, $, ko, proofViewModel, oscar */

/*
 * Command interface:
 *
 * var AbstractCommand = function (imageEditor) {
 *   // Run this command (preview)
 *   this.execute = function (params) {};
 *
 *   // Reverse edit (eg. cancel button)
 *   this.cancel = function () {};
 *
 *   // Confirm selection (apply button)
 *   this.apply = function () {};
 * };
 */


var CropCommand = function (imageEditor) {
    var jcropApi = null;
    var onSelect = imageEditor.options.cropOptions.onSelect;
    var onApply = imageEditor.options.cropOptions.onApply;
    var options = imageEditor.options.cropOptions;
    var selection = null;

    var onJCropSelect = function (coordinates) {
        if (coordinates) {
            selection = {
                x1: Math.floor(coordinates.x),
                y1: Math.floor(coordinates.y),
                x2: Math.floor(coordinates.x2),
                y2: Math.floor(coordinates.y2)
            };
        } else {
            selection = null;
        }

        if (onSelect) {
            onSelect(coordinates);
        }
    };

    /*
     * Set initial selection to about 80 % of original image
     */
    var setInitialSelection = function () {
        var dimensions = jcropApi.getBounds(),
            x_dist = dimensions[0] / 10,
            y_dist = dimensions[1] / 10;
        jcropApi.setSelect([
            x_dist, y_dist, dimensions[0] - x_dist, dimensions[1] - y_dist
        ]);
    };

    this.execute = function () {
        options.trueSize = [imageEditor.width, imageEditor.height];
        options.onSelect = onJCropSelect;
        // Use onChange only when integrated with external preview
        // (it fires up many events, turn it off when not needed)
        options.onChange = onSelect ? onJCropSelect : null;

        imageEditor.image.Jcrop(options, function () {
            jcropApi = this;
            setInitialSelection();
        });
    };

    this.cancel = function () {
        if (jcropApi) {
            jcropApi.destroy();
        }
        onJCropSelect(null);
    };

    this.apply = function () {
        imageEditor.requestTransformation({
            transformation: 'crop',
            x1: selection.x1,
            y1: selection.y1,
            x2: selection.x2,
            y2: selection.y2
        }, function (data) {
            if (onApply) {
                onApply(data.src, data.width, data.height);
            }
            jcropApi.destroy();
            imageEditor.onCommandFinished();
        });
    };
};


var GrayscaleCommand = function (imageEditor) {
    var originalImage = null;
    var onChange = imageEditor.options.grayscaleOptions.onChange;

    this.execute = function () {
        originalImage = imageEditor.image.attr('src');
        imageEditor.requestTransformation({
            transformation: 'grayscale'
        }, function (data) {
            if (onChange) {
                onChange(data.src);
            }
        });
    };

    this.cancel = function () {
        imageEditor.image.attr('src', originalImage);
        imageEditor.image.change();
        originalImage = null;
        if (onChange) {
            onChange(imageEditor.image.attr('src'));
        }
    };
    this.apply = function () {
        originalImage = null;
        if (onChange) {
            onChange(imageEditor.image.attr('src'));
        }
        imageEditor.onCommandFinished();
    };
};


var RotateCommand = function (imageEditor) {
    var angle = null;
    var onApply = imageEditor.options.rotateOptions.onApply;

    this.execute = function (new_angle) {
        angle = new_angle;
    };
    this.rollback = function () {};
    this.apply = function () {
        imageEditor.requestTransformation({
            transformation: 'rotate',
            angle: angle
        }, function (data) {
            if (onApply) {
                onApply(data.src, data.width, data.height);
            }
            imageEditor.onCommandFinished();
        });
    };
};


var RemoveCommand = function (imageEditor) {
    this.execute = function () {};
    this.cancel = function () {};
    this.apply = function () {
        imageEditor.image.attr('src', '');
        imageEditor.image.change();
        imageEditor.hide();
        imageEditor.onCommandFinished();
    };
};

var defaultOptions = {
    // {minSize: 400, boxWidth: 340, onSelect: function, onApply: function}
    cropOptions: {},
    // {onChange: function}
    grayscaleOptions: {},
    // {onApply: function}
    rotateOptions: {},
    // Should be live proof updated after command if available?
    enableLiveProof: false,
    // Should the remove button be displayed?
    enableRemove: false
};


var ImageEditor = function (image, apiBaseRoot, options) {
    var self = this;
    this.image = image;
    this.width = null;
    this.height = null;
    this.options = $.extend({}, defaultOptions, options);
    // Expect apiBaseRoot to end with '/'
    if (apiBaseRoot.slice(-1) === '/') {
        this.apiBaseRoot = apiBaseRoot;
    } else {
        this.apiBaseRoot = apiBaseRoot + '/';
    }

    this.init = function (width, height) {
        this.width = width;
        this.height = height;
        // cancel previous command
        this.cancel();
        this.croppable(this.canBeCropped());
        this.image.show();
        this.ready(true);
    };

    this.hide = function () {
        this.image.hide();
        this.ready(false);
    };

    /*
     * Command: Command object to run
     * Arguments: Arguments for the command, e.g. angle for rotation
     * setAsCurrent: wait for confirmation
     */
    this.runCommand = function (command, cmd_arguments, setAsCurrent) {
        if (command !== this.currentCommand()) {
            this.cancel();
        }
        command.execute.apply(command, cmd_arguments || []);
        if (setAsCurrent) {
            this.currentCommand(command);
        } else {
            command.apply();
        }
    };

    this.apply = function () {
        if (this.currentCommand()) {
            this.currentCommand().apply();
        }
    };

    this.cancel = function () {
        if (this.currentCommand()) {
            this.currentCommand().cancel();
            this.currentCommand(null);
        }
    };

    /*
     * Send request to server to edit image and handle it
     */
    this.requestTransformation = function (data, handler) {
        self.ready(false);
        self.image.parent().addClass('loading');
        data.src = self.image.attr('src');
        var url = self.apiBaseRoot + 'images/transformations/';
        $.ajax({
            type: "POST",
            url: url,
            data: data,
            async: true,
            cache: false,
            dataType: "json",
            headers: {'X-CSRFToken': getCookie('csrftoken')},
            success: function (data) {
                // update image data
                self.image.attr('src', data.src);
                self.width = data.width;
                self.height = data.height;
                self.croppable(self.canBeCropped());
                self.image.change();

                if (handler) {
                    handler(data);
                }

                self.ready(true);
                self.image.parent().removeClass('loading');
            },
            error: function (xhr) {
                oscar.messages.error('Image editor error: ' + xhr.responseText);
                self.cancel();
            }
        });
    };

    /*
     * Operations after a command was applied or canceled
     */
    this.onCommandFinished = function () {
        // Request live proof if enabled
        if (self.options.enableLiveProof) {
            proofViewModel.requestLiveProof();
        }
        this.image.css('width', 'auto');
        this.image.css('height', 'auto');
        this.currentCommand(null);
    };

    /*
     * Knockout stuff
     */
    this.ready = ko.observable(false);
    this.croppable = ko.observable(true);
    this.currentCommand = ko.observable(null);
    this.changed = ko.computed(function () {
        return self.currentCommand() !== null;
    });

    /* Allow cropping if the image size is at least minSize */
    this.canBeCropped = function () {
        var minSize = self.options.cropOptions.minSize;
        return (typeof minSize === "undefined") || (self.width > minSize[0] && self.height > minSize[1]);
    };

    /*
     * Commands
     */
    var cropCommand = new CropCommand(this);
    this.crop = function () {
        this.runCommand(cropCommand, [], true);
    };

    var grayscaleCommand = new GrayscaleCommand(this);
    this.grayscale = function () {
        this.runCommand(grayscaleCommand, [], true);
    };

    var rotateCommand = new RotateCommand(this);
    this.rotate = function (angle) {
        this.runCommand(rotateCommand, [angle], false);
    };

    var removeCommand = new RemoveCommand(this);
    this.remove = function () {
        this.runCommand(removeCommand, [], false);
    };
};
