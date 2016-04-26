// validate email
function validateEmail(email){
	var re = /^[a-z0-9\.\-\_]+@[a-z0-9\.\-\_]+(\.[a-z0-9\.\-\_]+){1,4}$/ ;
	return re.test(email.toLowerCase())
}

// string trim
if (! String.prototype.trim){
	String.prototype.trim = function(){
		return this.replace(/^\s+|\s+$/g, '') ;
	}
}

// init console
if (! window.console){
	window.console = {
		log : function(){},
		info : function(){} ,
		error : function(){},
		warn: function(){} ,
		debug: function(){}
	}
}

// form extends
$(function(){
	$.fn.extend({
		showFormError : function(err) {
			return this.each(function() {
				var 
				$form = $(this), 
				$alert = $form && $form.find('.uk-alert-danger'),
				fieldName = err && err.data ;
			if (!$form.is('form')){
				console.error('Cannot call showFormError() on non-form object.')
				return ;
			}
			$form.find('input').removeClass('uk-form-danger') ;
			$form.find('select').removeClass('uk-form-danger') ;
			$form.find('textarea').removeClass('uk-form-danger') ;
			if ($alert.length === 0){
				console.warn('Cannot find .uk-alert-danger element.') ;
				return ;
			}
			if (err){
				$alert.text(err.message ? err.message : (err.error ? err.error : err)).removeClass('uk-hidden').show() ;
				if (($alert.offset().top - 60) < $(window).scrollTop()){
					$('html,body').animate({scrollTop:$alert.offset().top - 60})
				}
				if (fieldName){
					$form.find('[name=' + fieldName + ']').addClass('uk-form-danger') ;
				}
			}else{
				$alert.addClass('uk-hidden').hide() ;
				$form.find('.uk-form-danger').removeClass('uk-form-danger') ;
			}
			});
		},
		
		showFormLoading : function(isLoading){
			return this.each(function(){
				var 
				$form = $(this),
				$submit = $form && $form.find('button[type=submit]'),
				$buttons = $form && $form.find('button') ,
				$i = $submit && $submit.find('i'),
				iconClass = $i && $i.attr('class') ;
				if (!$form.is('form')){
					console.error('Cannot call showFormError() on non-form object.')
					return ;
				}
				if (!iconClass || iconClass.indexOf('uk-icon') < 0){
					console.warn('Icon <i class="uk-icon-*>" not found.');
					return ;
				}
				if (isLoading) {
					$buttons.attr('disabled', 'disabled') ;
					$i && $i.addClass('uk-icon-spinner').addClass('uk-icon-spin') ;
				}else{
					$buttons.removeAttr('disabled');
					$i && $i.removeClass('uk-icon-spinner').removeClass('uk-icon-spin');
				}
			})
		},
		
		postJSON : function(url, data, callback){
			if (arguments.length === 2){
				callback = data ;
				data = {} ;
			}
			return this.each(function(){
				var $form = $(this) ;
				$form.showFormError() ;
				$form.showFormLoading(true) ;
				$.ajax({
					url : url,
					data : data,
					type : 'POST',
					dataType : 'json',
					error : function(jqXHR, textStatus){
						$form.showFormError({'error':'http_bad_response','data':''+jqXHR.status,'message':'网络好像出问题了呢(HTTP'+jqXHR.status+')'})
						$form.showFormLoading(false) ;
					},
					success : function(r){
						if (r && r.error){
							$form.showFormError(r) ;
							$form.showFormLoading(false) ;
						}else{
							return callback(null, r) ;
						}
					}
				})
				
			})
		}
	})
})