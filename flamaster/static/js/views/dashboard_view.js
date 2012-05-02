// Generated by CoffeeScript 1.3.1
var __hasProp = {}.hasOwnProperty,
  __extends = function(child, parent) { for (var key in parent) { if (__hasProp.call(parent, key)) child[key] = parent[key]; } function ctor() { this.constructor = child; } ctor.prototype = parent.prototype; child.prototype = new ctor; child.__super__ = parent.prototype; return child; };

define(['chaplin/view', 'text!templates/dashboard.hbs'], function(View, template) {
  'use strict';

  var DashboardView;
  return DashboardView = (function(_super) {

    __extends(DashboardView, _super);

    DashboardView.name = 'DashboardView';

    function DashboardView() {
      return DashboardView.__super__.constructor.apply(this, arguments);
    }

    DashboardView.prototype.autoRender = true;

    DashboardView.prototype.containerSelector = '#content';

    DashboardView.prototype.id = 'dashboard';

    DashboardView.template = template;

    return DashboardView;

  })(View);
});