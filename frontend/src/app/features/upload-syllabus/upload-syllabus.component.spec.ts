import { ComponentFixture, TestBed } from '@angular/core/testing';

import { UploadSyllabus } from './upload-syllabus';

describe('UploadSyllabus', () => {
  let component: UploadSyllabus;
  let fixture: ComponentFixture<UploadSyllabus>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadSyllabus]
    })
    .compileComponents();

    fixture = TestBed.createComponent(UploadSyllabus);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
