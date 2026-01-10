(function($) {
    'use strict';
    
    $(document).ready(function() {
        function toggleSpecialityField() {
            var roleField = $('#id_role');
            var specialityField = $('#id_speciality_id').closest('.form-row');
            var specialityLabel = specialityField.find('label');
            
            if (roleField.val() === 'mentor') {
                specialityField.show();
                specialityLabel.find('span').remove();
                if (!specialityLabel.find('span').length) {
                    specialityLabel.append(' <span style="color: red;">*</span>');
                }
            } else {
                specialityField.hide();
                $('#id_speciality_id').val('');
            }
        }
        
        // Toggle on page load
        toggleSpecialityField();
        
        // Toggle on role change
        $('#id_role').on('change', function() {
            toggleSpecialityField();
        });
    });
})(django.jQuery);
